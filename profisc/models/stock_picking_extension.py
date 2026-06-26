import json, logging, requests
import uuid
import pytz
import qrcode
import base64
from io import BytesIO
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime

_logger = logging.getLogger(__name__)


def get_wtn_issuer(company):
    return {
        "Name": company.name,
        "NIPT": company.vat,
        "Address": company.street,
        "City": company.city
    }


class StockPickingExtension(models.Model):
    _inherit = ['stock.picking']

    profisc_qr_code_img = fields.Binary("QR Code", attachment=True)
    profisc_fisc_type = fields.Char(string='Fiscalization Type')
    profisc_fisc_status = fields.Char(string='Fiscal Status')
    profisc_iic = fields.Char(string='IIC')
    profisc_fic = fields.Char(string='FIC')
    profisc_qr_code = fields.Char(string='Qr Url')
    profisc_fisc_downloaded = fields.Boolean(string='Fiscal Downloaded')
    profisc_fic_error_code = fields.Char(string='FIC Error Code')
    profisc_fic_error_description = fields.Char(string='FIC Error Description')
    profisc_ubl_id = fields.Char(string='UBL ID')

    profisc_status_control = fields.Selection([('0', 'In Process'), ('2', 'Error'), ('3', 'Success'), ],
                                              string='Status Control')

    profisc_currency_id = fields.Many2one('res.currency', string='Currency')
    profisc_transaction_type = fields.Selection(
        [('TRANSFER', 'Transfer'), ('DORE', 'Dore'), ('SALES', 'Sales'), ('EXAMINATION', 'Examination')],
        string='TransactionType', default='TRANSFER')
    profisc_total = fields.Float(string='Profisc Total', digits=(10, 2), readonly=True)
    profisc_items_num = fields.Integer(string='Items num', readonly=True)
    profisc_vehicle_ownership = fields.Selection([('OWNER', 'Owner'), ('THIRDPARTY', 'Third Party')],
                                                 string='VehOwnership', default='OWNER')

    profisc_vehicle_plate = fields.Many2one('profisc.wtn_vehicles', string='VehiclePlate',
                                            states={'done': [('readonly', True)]})
    profisc_wtn_type = fields.Selection([('n_a', 'None'), ('WTN', 'Wtn'), ('SALE', 'Sale')], string='Wtn type',
                                        states={'done': [('readonly', True)]}, default='WTN')
    profisc_destin_date = fields.Datetime(string='Destin Date', store=True,
                                          default=fields.Datetime.now, tracking=True,
                                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                                          help="Specify the moment when the package it's going to arrive at the "
                                               "specified destination")
    profisc_invoice_id = fields.Char(string='Invoice Id', default=uuid.uuid4(), states={'done': [('readonly', True)]})
    profisc_is_goods_flammable = fields.Boolean(string='Is Goods Flammable')
    profisc_is_escort_required = fields.Boolean(string='Is Escort Required')

    # profisc_bu_id = fields.Many2one('profisc.business_units', string='Business Unit',
    #                                 domain=lambda self: [('company_id', '=', self.env.company.id)])

    profisc_bu_code = fields.Selection(selection='_get_business_units', string='Business Unit')
    profisc_subseq = fields.Selection([
        ('NOINTERNET', 'NO INTERNET'),
        ('SERVICE', 'SERVICE'),
        ('TECHNICALERROR', 'TECHNICAL ERROR'),
        ('BOUNDBOOK', 'BOUNDBOOK'),
    ], store=True, string='Subseq')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'stock.picking')],
        string='Attachments'
    )

    is_internal = fields.Boolean(compute='_compute_is_internal')

    def _generate_qr(self):
        for rec in self:
            if rec.profisc_qr_code:
                qr = qrcode.make(rec.profisc_qr_code)
                buffer = BytesIO()
                qr.save(buffer, format="PNG")
                rec.profisc_qr_code_img = base64.b64encode(buffer.getvalue())
            else:
                _logger.info("Nuk u gjenerua nje qr kod")

    @api.depends('picking_type_code', 'profisc_wtn_type')
    def _compute_is_internal(self):
        for record in self:
            is_internal = False
            if record.picking_type_code == 'internal':
                if record.profisc_wtn_type not in ('n_a', False):
                    is_internal = True

            record.is_internal = is_internal

    def get_wtn_carrier(self):
        for record in self:
            partner = record.partner_id
            if not partner.id:
                self.error(record.id, "Please choose a carrier")

            vat_type = 'ID'
            id_num = 'A12345678B'
            if partner.profisc_customer_vat_type:
                pcv = partner.profisc_customer_vat_type
                if pcv == '9923':
                    vat_type = 'NUIS'
            if partner.vat and len(partner.vat) > 0:
                id_num = partner.vat

            return {
                "IDType": vat_type,
                "IDNum": id_num,
                "Name": partner.display_name,
                "Town": partner.city,
                "Address": partner.street
            }

    def _update_fisc(self, res):

        log_type = 'Success'
        data_to_write = {
            'profisc_ubl_id': res['wtnNum'],
            'profisc_iic': res['wtnic'],
            'profisc_qr_code': res['qrUrl']
        }
        if res['errorCode'] and res['errorCode'] is not None:
            data_to_write['profisc_status_control'] = '2'
            data_to_write['profisc_fic_error_code'] = res['errorCode']
            data_to_write['profisc_fic_error_description'] = res['faultDescription']
            message = f" Error me kod {res['errorCode']}, {res['faultDescription']}"
            log_type = 'Error'
        else:
            data_to_write['profisc_status_control'] = '3'
            data_to_write['profisc_fic'] = res['fwtnic']
            data_to_write['profisc_fic_error_code'] = ''
            data_to_write['profisc_fic_error_description'] = ''
            message = f"U fiskalizua me sukses me fwtnic {res['fwtnic']}"

        for record in self:
            record.write(data_to_write)
            self.writeActivity(record.id, message, log_type)

    def writeActivity(self, move_id, message, log_type):
        self.env['mail.message'].create({
            'model': 'stock.picking',
            'res_id': move_id,
            'message_type': 'comment',
            'body': f"{log_type} action in fiscalization:<br/> {message}",
        })

    def _get_business_units(self):
        bus = self.env['profisc.business_units'].search([('company_id', '=', self.env.company.id)])
        return [(bu.code, bu.code) for bu in bus]

    def createRequest(self, payload):

        payload_object = {
            "file": self.env['other_functions'].dict_to_base64(payload),
            "internal_id": payload['WTN'][0]['WTNHeader']['InvoiceID']
        }
        return payload_object

    def send_to_profisc(self):
        for record in self:
            if record.profisc_wtn_type == 'n_a':
                return

            request_manager = self.env['request.manager']

            issuer = get_wtn_issuer(record.location_id.company_id)
            carrier = self.get_wtn_carrier()
            wtn_lines = self._get_items()
            header = self._getHeader()

            payload_json = {"WTN": [{
                'WTNHeader': header,
                'WTNIssuer': issuer,
                'WTNCarrier': carrier,
                'WNTLines': wtn_lines
            }]}
            payload = self.createRequest(payload_json)

            company = self.env['profisc.auth'].get_current_company()

            _logger.info('stock_picking_extension>send_to_profisc> %s' % payload)
            endpoint = f"{company.profisc_api_endpoint}{company.profisc_upload_wtn_invoice}"
            try:
                res = request_manager.post_with_header(endpoint, payload=payload)
                if res:
                    self._update_fisc(res)
                    _logger.info('stock_picking_extension>response> %s' % res)
            except requests.RequestException as e:
                self.writeActivity(record.id, f"Failed to make request:{e}", "Error")
                _logger.error('Failed to make request: %s', e)
                raise

    def error(self, move_id, message):
        self.writeActivity(move_id, message, "Error")
        raise UserError(message)

    def info(self, move_id, message):
        self.writeActivity(move_id, message, "Info")

    def get_pdf(self):
        for record in self:
            try:
                company = self.env['profisc.auth'].get_current_company()
                request_manager = self.env['request.manager']

                payload = {
                    "object": "GetWtnPDF",
                    "params": json.dumps({"wtnic": record.profisc_iic}),
                    "username": self.env.user.name,
                    "company": company.profisc_company_id
                }

                _logger.info('stock_picking_extension>get_pdf> %s' % payload)
                endpoint = f"{company.profisc_api_endpoint}{company.profisc_search_endpoint}"
                res = request_manager.post_with_header(endpoint, payload=payload)
                if res:
                    _logger.info('get_pdf>response> %s' % res)
                    return self.getFile(res)
            except requests.RequestException as e:
                self.writeActivity(record.id, f"Failed to make request:{e}", "Error")
                _logger.error('Failed to make request: %s', e)
                raise

    def getFile(self, res):
        for record in self:
            if res['status'] and res['error'] is None and len(res['content']) > 0:
                content = res['content'][0]
                self.add_attachment(record, content)
                return None
            else:
                self.error(record.id, "Requested file not found.")

            return {'success': True, "status_code": 100, "message": "Veprim i suksesshem"}

    def add_attachment(self, record, attachment_data):

        # _logger.info('attachment_data:: %s!'  %(attachment_data))
        attachment_data_bytes = attachment_data.encode('utf8').decode('ascii')
        attachment_vals = {
            'name': "wtn_invoice",
            'datas': attachment_data_bytes,
            'res_model': "stock.picking",
            'res_id': record.id,
        }
        attachment = self.env['ir.attachment'].create(attachment_vals)
        record.write({'attachment_ids': [(4, attachment.id)], "profisc_fisc_downloaded": True})

    def _getHeader(self):
        for record in self:
            start_wh = record.location_id.warehouse_id
            end_wh = record.location_dest_id.warehouse_id

            if start_wh.id == end_wh.id:
                message = "The source and destination locations shouldn't be the same"
                self.error(record.id, message)
            if not record.profisc_destin_date:
                message = "Please, choose the destination date"
                self.error(record.id, message)
            if not record.profisc_vehicle_plate:
                message = "Please, choose the Vehicle"
                self.error(record.id, message)
            if not record.profisc_vehicle_plate:
                message = "Please, choose the Vehicle"
                self.error(record.id, message)
            if not record.profisc_bu_code:
                message = "Please, choose the Business Unit"
                self.error(record.id, message)

            tirana_timezone = pytz.timezone('Europe/Belgrade')

            today = datetime.now().date()
            iso_format_date = today.isoformat()

            header = {
                "InvoiceID": record.profisc_invoice_id,
                "WTNType": record.profisc_wtn_type,
                "ItemsNum": record.profisc_items_num,
                "TransactionType": record.profisc_transaction_type,
                "BUCode": record.profisc_bu_code,
                "VehOwnership": record.profisc_vehicle_ownership,
                "VehPlate": record.profisc_vehicle_plate.plate,
                "StartAddr": start_wh.partner_id.street,
                "StartCity": start_wh.partner_id.city,
                "StartPoint": start_wh.profisc_start_point,
                "IssueDate": str(record.date_done.astimezone(tirana_timezone).isoformat()),
                "StartDate": str(record.date_done.astimezone(tirana_timezone).isoformat()),
                "DestinAddr": end_wh.partner_id.street,
                "DestinCity": end_wh.partner_id.city,
                "DestinPoint": end_wh.profisc_start_point,
                "DestinDate": str(record.profisc_destin_date.astimezone(tirana_timezone).isoformat()),
                "IsGoodsFlammable": record.profisc_is_goods_flammable,
                "IsEscortRequired": record.profisc_is_escort_required,
                "ValueOfGoods": record.profisc_total
            }

            if record.user_id.profisc_operator_code:
                header['OperatorCode'] = record.user_id.profisc_operator_code
            if record.profisc_subseq:
                header['Subseq'] = record.profisc_subseq

            return header

    def _get_items(self):
        wtn_products = []
        for record in self:

            profisc_total = 0.0
            items_num = 0.0
            for move_line in record.move_line_ids:
                product = move_line.product_id
                items_num += 1
                profisc_total += move_line.qty_done * product.standard_price

                uom_code = product.uom_id.profisc_uom_val.code if product.uom_id.profisc_uom_val else product.uom_id.name

                wtn_product = {
                    "WTNNum": None,
                    "LineID": move_line.move_id.sequence,
                    "LineNum": None,
                    "ItemCode": product.default_code if product.default_code else '',
                    "ItemName": product.name,
                    # "ItemMU": move_line.product_uom_id.name if move_line.product_uom_id.name else 'XPP',
                    "ItemMU": uom_code,
                    # "ItemMU": 'COPE',
                    "ItemQty": move_line.qty_done
                }
                _logger.info(f"uom_code:{uom_code}")

                wtn_products.append(wtn_product)

            record.profisc_total = profisc_total
            record.profisc_items_num = items_num

        return wtn_products
