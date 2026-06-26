import json
import logging
import textwrap
from collections import defaultdict
from datetime import date, datetime

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def userError(key, dict_ob):
    if key in dict_ob:
        raise UserError(dict_ob[key])
    raise UserError(json.dumps(dict_ob))


def get_difference_in_days(start_date):
    today_dt = datetime.now()
    return (today_dt - start_date).days


def generate_payment_methods(record):
    merged_list = []
    invoice_payments = []
    for pmt in record.payment_ids:
        payment_method = pmt.payment_method_id.profisc_payment_method
        invoice_pmt = {
            "paymentTerm": payment_method.code,
            "bankorCash": payment_method.name,
            "paymentAmount": pmt.amount
        }

        invoice_payments.append(invoice_pmt)
        merged_data = defaultdict(lambda: {"paymentTerm": "", "bankorCash": "", "paymentAmount": 0})
        for item in invoice_payments:
            key = item["bankorCash"]
            merged_data[key]["paymentTerm"] = item["paymentTerm"]
            merged_data[key]["bankorCash"] = item["bankorCash"]
            merged_data[key]["paymentAmount"] += item["paymentAmount"]
        merged_list = list(merged_data.values())

    return merged_list


class PosOrder(models.Model):
    _inherit = 'pos.order'

    profisc_fisc_type = fields.Char(string='Fiscalization Type', store=True)
    profisc_fisc_status = fields.Char(string='Fiscal Status', store=True)
    profisc_iic = fields.Char(string='IIC', store=True)
    profisc_fic = fields.Char(string='FIC')
    profisc_eic = fields.Char(string='EIC')
    profisc_erp_id = fields.Char(string='Erp Id')
    profisc_qr_code = fields.Char(string='Qr Url')
    profisc_qr_code_check = fields.Binary(string='Qr Code', attachment=True)
    profisc_fisc_downloaded = fields.Boolean(string='Fiscal Downloaded')
    profisc_fic_error_code = fields.Char(string='FIC Error Code')
    profisc_fic_error_description = fields.Char(string='FIC Error Description')
    profisc_eic_error_code = fields.Char(string='EIC Error Code')
    profisc_eic_error_description = fields.Char(string='EIC Error Description')
    profisc_ubl_id = fields.Char(string='UBL ID')
    profisc_status_control = fields.Selection([('0', 'In Process'), ('2', 'Error'), ('3', 'Success'), ], store=True,
                                              string='Status Control')
    is_draft = fields.Boolean(string="Is Draft", default=True)
    sent_fiscal = fields.Boolean(string="Send to Fiscalization", default=False)

    @api.model
    def import_rescued_orders(self):
        order_attachments = self.env['ir.attachment'].search([('name', 'ilike', 'pos_order_save_')])

        for order_attachment in order_attachments:
            self.env['pos.order'].create_from_ui([json.loads(order_attachment.raw)])


    def _get_refund_origin(self, order):

        possible_fields = [
            "refunded_order_id",
            "return_order_id",
            "origin_id",
        ]

        for field in possible_fields:
            origin = getattr(order, field, False)
            if origin:
                return origin

        return None

    @api.model
    def profisc_resend(self, subseq, invoice_ids):
        # browse i kthe n rekorde pos-i qe te kapim state si fush me bo checkun
        orders = self.browse(invoice_ids)

        company = self.env['profisc.auth'].get_current_company()
        payload = {
            "object": "profisc_resend",
            "value": subseq,
            "username": self.env.user.name,
            "company": company.profisc_company_id,
            "invoice_ids": invoice_ids
        }
        _logger.info(f"profisc_resend %s", payload)
        for order in orders:
            if order.state not in ('done', 'paid'):
                raise UserError("This order is not yet finalized.")
            self.fiscalize_order(order.id, subseq)

        return payload

    def action_show_update_profisc_subseq_wizard(self):
        return {
            'name': 'Update Profisc Subseq',
            'type': 'ir.actions.act_window',
            'res_model': 'profisc.pos_order_wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('profisc.view_update_profisc_subseq_wizard').id,
            'target': 'new',
        }

    def action_finalize_order(self):
        """Manual action to finalize and fiscalize the order.
        Also used to retry fiscalization after timeout/connection errors.
        """
        for order in self:
            if order.profisc_status_control == '3':
                raise UserError("This order has already been fiscalized successfully.")

            _logger.info("Manually finalizing order ID: %s (current status: %s)",
                         order.id, order.profisc_fisc_status)
            # Set is_draft to False
            order.write({'is_draft': False})
            # Call fiscalization
            self.fiscalize_order(order.id, 'n_a')

        # Check if fiscalization succeeded after the call
        order.invalidate_recordset()
        if order.profisc_status_control == '3':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Order Finalized',
                    'message': 'The order has been fiscalized successfully.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Fiscalization Failed',
                    'message': f'Error: {order.profisc_fic_error_description or "Unknown error"}. Please try again.',
                    'type': 'warning',
                    'sticky': True,
                }
            }

    @api.model
    def get_invoice(self, order_ref):
        invoice = self.env['pos.order'].search(
            [('pos_reference', '=', order_ref)], limit=1)
        return {
            'profisc_ubl_id': invoice.profisc_ubl_id,
            'profisc_iic': invoice.profisc_iic,
            'profisc_fic': invoice.profisc_fic,
            'profisc_eic': invoice.profisc_eic,
            'profisc_qr_code': invoice.profisc_qr_code,
            'profisc_fic_error_code': invoice.profisc_fic_error_code,
            'profisc_fic_error_description': invoice.profisc_fic_error_description
        }

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)

        # Include your custom fields
        fields["profisc_fisc_type"] = ui_order.get("profisc_fisc_type", False)
        # Default to True (draft) to prevent automatic fiscalization
        # Only Validate button should explicitly set this to False
        fields["is_draft"] = ui_order.get("is_draft", True)
        # New flag: only fiscalize when explicitly set to True by Validate button
        fields["sent_fiscal"] = ui_order.get("sent_fiscal", False)

        return fields



    @api.model
    def _process_order(self, order, existing_order):
        order_id = super(PosOrder, self)._process_order(order, existing_order)

        sent_fiscal = order.get('sent_fiscal', False)
        _logger.info("Processing order ID: %s, sent_fiscal: %s", order_id, sent_fiscal)

        # Only fiscalize when sent_fiscal flag is explicitly True (set by Validate button)
        # All other cases: auto-sync, kitchen orders, draft button -> sent_fiscal=False -> skip fiscalization
        if sent_fiscal:
            _logger.info("Fiscalizing order (Validate button pressed). Order ID: %s", order_id)
            result = self.fiscalize_order(order_id, 'n_a')
            return result or order_id
        else:
            _logger.info("Skipping fiscalization (sent_fiscal=False). Order ID: %s", order_id)
            return order_id

    @api.model
    def fiscalize_order(self, order_id, subseq):
        _logger.info('fiscalize_order with id: %s and subseq %s', order_id, subseq)
        pos_order = self.browse(order_id)

        _logger.info(f'erpIdIfResend:: {pos_order.profisc_erp_id}')

        if(pos_order.profisc_erp_id is False):
            erp_id_without_timestamp = pos_order.pos_reference.replace(" ", "").lower()+str(order_id)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Format as YYYYMMDDHHMMSS
            pos_order.profisc_erp_id = f"{erp_id_without_timestamp}-{timestamp}"
            self.env.cr.commit()

        order_identif_log = {"id": order_id, "erp_id": pos_order.profisc_erp_id, "reference": pos_order.pos_reference}

        profisc_fisc_type = int(pos_order.profisc_fisc_type or 0)
        if profisc_fisc_type == 3:
            _logger.info("Creating FK...")
            return order_id

        order = self.browse(order_id)

        if not order:
            _logger.error("fiscalize_order called with invalid order_id=%s", order_id)
            return False

        amount_total = order.amount_total
        config = order.session_id.config_id if order.session_id else False
        max_amount = config.max_pos_payment_amount if config else 0.0

        _logger.info(
            "Checking POS max amount before fiscalization | "
            "order_id=%s total=%s max=%s",
            order.id,
            amount_total,
            max_amount
        )

        if not order.partner_id and max_amount and amount_total > max_amount:
            _logger.error(
                "FISCALIZATION BLOCKED | order=%s total=%s max=%s",
                order.id,
                amount_total,
                max_amount
            )
            raise ValidationError(
                _(
                    "Order total %(total)s exceeds maximum allowed %(max)s",
                    total=amount_total,
                    max=max_amount,
                )
            )

        company = self.env['profisc.auth'].get_current_company()
        invoice_payload = self.createInvoicePayload(pos_order)
        if subseq != 'n_a':
            invoice_payload['subseq'] = subseq

        auth_object = {
            "object": invoice_payload,
            "invoiceId": pos_order.profisc_erp_id,
            "invoiceType": 'invoice',
            "isEinvoice": int(pos_order.profisc_fisc_type) == 2,
        }
        _logger.info('pos_order.profisc_fisc_type:: %s' % pos_order.profisc_fisc_type)
        _logger.info('request:: %s' % auth_object)
        try:
            response = requests.post(
                f"{company.profisc_api_endpoint}{company.profisc_upload_invoice}",
                data=json.dumps(auth_object),
                headers=self.env['profisc.auth'].generateHeaders(),
                timeout=30,
            )
            res = response.json()
        except requests.exceptions.Timeout:
            _logger.error('ProFisc API timeout for order %s (erp_id=%s)', order_id, pos_order.profisc_erp_id)
            pos_order.write({
                'profisc_status_control': '2',
                'profisc_fisc_status': 'ETIMEOUT',
                'profisc_fic_error_code': 'TIMEOUT',
                'profisc_fic_error_description': 'Fiscalization server timeout — retry from order form.',
            })
            self.env.cr.commit()
            return order_id
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            _logger.error('ProFisc API connection error for order %s: %s', order_id, e)
            pos_order.write({
                'profisc_status_control': '2',
                'profisc_fisc_status': 'ECONN',
                'profisc_fic_error_code': 'CONNECTION',
                'profisc_fic_error_description': f'Fiscalization server unreachable — retry from order form. ({e})',
            })
            self.env.cr.commit()
            return order_id
        except (ValueError, requests.exceptions.JSONDecodeError) as e:
            _logger.error('ProFisc API returned invalid/empty response for order %s: %s', order_id, e)
            pos_order.write({
                'profisc_status_control': '2',
                'profisc_fisc_status': 'EPARSE',
                'profisc_fic_error_code': 'EMPTY_RESPONSE',
                'profisc_fic_error_description': f'Fiscalization server returned empty/invalid response — retry from order form. ({e})',
            })
            self.env.cr.commit()
            return order_id

        _logger.info('response:: %s' % res)
        self.handleResponse(pos_order, res, response, subseq)
        # Call the super function to ensure original functionalities are retained
        return order_id

    def handleResponse(self, record, res, response, subseq):
        _logger.info('response.status_code:: %s!' % response.status_code)

        if response.status_code == 200:
            if res['status'] and res['errorCode'] is None:
                self.updateRecord(record, res)
                # self.getQrCode(record.id)
                # self.info(record.id, "Fiskalizim i suksesshem")

            elif res['errorCode'] == 'T991':
                record.write({
                    'profisc_status_control': '2',
                    'profisc_fisc_status': 'E' + res['errorCode'],
                    'profisc_fic_error_code': res['errorCode'],
                    'profisc_eic_error_description': res['faultDescription'],
                    'profisc_iic': res['iic'],
                    'profisc_fic': res['fic'],
                    'profisc_eic': res['eic'],
                    'profisc_qr_code': self._qr_url_to_data_uri(res.get('qrUrl', ''))
                })
                self.env.cr.commit()

            elif res['errorCode'] == 'T010':
                self.updateRecord(record, res)

            else:
                record.write({
                    'profisc_status_control': '0',
                    'profisc_fisc_status': 'E' + res['errorCode'],
                    'profisc_fic_error_code': res['errorCode'],
                    'profisc_fic_error_description': res['faultDescription']
                })
                self.env.cr.commit()
                userError('faultDescription', res)

            # raise UserError("Error with code:"+res['errorCode']+", description:"+res['faultDescription'])
        elif response.status_code in (401, 403):
            self.env['profisc.auth'].profisc_login()
            self.fiscalize_order(record.id, subseq)
        else:
            userError('faultDescription', res)

    def _qr_url_to_data_uri(self, url):
        """Convert a QR code URL to a data:image/png;base64 URI for POS receipt display."""
        if not url:
            return url
        try:
            encoded = self.env['other_functions'].createQrCode(url)
            return 'data:image/png;base64,' + encoded
        except Exception as e:
            _logger.error('Failed to generate QR code image: %s', e)
            return url

    def updateRecord(self, record, res):
        record.write({
            'profisc_iic': res['iic'],
            'profisc_fic': res['fic'],
            'profisc_eic': res['eic'],
            'profisc_qr_code': self._qr_url_to_data_uri(res.get('qrUrl', '')),
            'profisc_status_control': '3',
            'profisc_fisc_status': 'Y',
            'profisc_fic_error_code': '100',
            'profisc_fic_error_description': '',
            'profisc_ubl_id': res['ublId']

        })
        self._force_create_invoice(record)

    def createInvoicePayload(self, record):
        # _logger.info(
        #     "DEBUG REF CHECK | refunded_order_id=%s | return_order_id=%s | origin=%s | total=%s",
        #     getattr(record, "refunded_order_id", False),
        #     getattr(record, "return_order_id", False),
        #     getattr(record, "origin_id", False),
        #     record.amount_total,
        # )

        ref_order = self._get_refund_origin(record)
        is_refund = bool(ref_order)

        # _logger.info(
        #     "Refund detection => order=%s origin=%s has_iic=%s total=%s",
        #     record.name,
        #     ref_order.name if ref_order else None,
        #     # bool(getattr(ref_order, "profisc_iic", False)) if ref_order else False,
        #     # record.amount_total
        # )

        # --- Common invoice fields ---
        current_time = datetime.now().strftime("%H:%M:%S")
        company = self.env.company

        invoice_json = {
            "invoiceId": record.profisc_erp_id,
            'date': str(record.date_order.strftime("%d/%m/%Y ") + current_time),
            'dueDate': str(record.date_order.strftime("%d/%m/%Y ") + current_time),
            'invoiceCode': 384 if is_refund else 380,
            'invoiceType': "credit" if is_refund else "invoice",
            'currency': "ALL",
            'exchangeRate': 1,
            'sendEInv': int(record.profisc_fisc_type) == 2,
            'taxScheme':  company.tax_type,
            'profileId': "P10" if is_refund else "P1",
            'noteToCustomer': "",
            'customer': {
                "name": "Klient i pergjithshem",
                "nipt": "T12345678P",
                "address": "Tirane",
                "cityName": "Tirane",
                "countryCode": "ALB",
                "idType": "ID"
            },
            "seller": {
                "name": record.company_id.display_name,
                "nipt": record.company_id.vat,
                "address": record.company_id.street,
                "cityName": record.company_id.city,
                "countryCode": self.env['other_functions'].convert_country_code(record.company_id.country_code),
                # record.company_id.country_code
            },
            "paymentMethods": [],
            'items': [],
            'totalNeto': record.amount_total - record.amount_tax,
            'totalVat': record.amount_tax,
            'total': record.amount_total
        }
        if ref_order:
            invoice_json['refIic'] = str(ref_order.profisc_iic)  # new corrective
            invoice_json['refIssueDate'] = str(ref_order.write_date.strftime("%Y-%m-%d"))

        if record.config_id.tcr_code:
            invoice_json['tcr'] = record.config_id.tcr_code

        # if record.employee_id.

        if record.employee_id.profisc_operator_code:
            operator_code = record.employee_id.profisc_operator_code
        else:
            operator_code = record.user_id.profisc_operator_code

        if operator_code:
            invoice_json['operatorCode'] = operator_code

        _logger.info(f"operatorCode::{record.employee_id.profisc_operator_code}, name::{record.employee_id.name}")

        if record.partner_id.name:
            customer = {
                "name": record.partner_id.name,
                "nipt": record.partner_id.vat,
                "address": record.partner_id.street,
                "cityName": record.partner_id.city,
                "countryCode": self.env['other_functions'].convert_country_code(record.partner_id.country_code),
            }
            if record.partner_id.profisc_customer_vat_type:
                customer[
                    'idType'] = record.partner_id.profisc_customer_vat_type if record.partner_id.profisc_customer_vat_type else "id"
            else:
                customer['idType'] = "9923"

            invoice_json['customer'] = customer

        if len(record.payment_ids) > 0:
            invoice_payments = generate_payment_methods(record)
            invoice_json['paymentMethods'] = invoice_payments

        for line in record.lines:

            tax = line.tax_ids
            price_include = tax.price_include

            if line.customer_note:
                invoice_json['noteToCustomer'] += line.customer_note
                invoice_json['noteToCustomer'] += " "

            item_price = line.price_unit
            total_line_neto = line.price_subtotal

            if price_include:
                item_price = line.price_unit / (1 + tax.amount / 100)

            total_line_vat = total_line_neto * (1 + tax.amount / 100) - total_line_neto  # formula e pare

            coef = 1

            uom_code = line.product_uom_id.profisc_uom_val.code if line.product_uom_id.profisc_uom_val else line.product_uom_id.name

            invoice_line = {
                'code': str(line.id),
                'name': textwrap.shorten(line.full_product_name, width=50, placeholder="..."),
                "unit": uom_code,
                'quantity': coef * line.qty,
                'price': item_price,
                "discount": line.discount,  #
                "vat": tax.amount,
                "vatScheme": tax.profisc_vat_schema,
                "totalLineNeto": coef * total_line_neto,
                "totalLineVat": coef * total_line_vat
            }

            _logger.info(f"uom_code:{uom_code}")
            invoice_json['items'].append(invoice_line)

        self.set_sub_seq(invoice_json)

        return invoice_json

    def _create_invoice(self, move_vals):  # Match original signature
        # Call super to get the original functionality for creating an invoice

        invoice = super(PosOrder, self)._create_invoice(move_vals)

        _logger.info("Method _create_invoice is called %id" % invoice.id)
        _logger.info("Creating Invoice for Order(s): %s", self.ids)
        for order in self:
            _logger.info("BEFORE super | order=%s iic=%s fic=%s",
                         order.name,
                         order.profisc_iic,
                         order.profisc_fic)

            invoice.write({
                'profisc_iic': order.profisc_iic,
                'profisc_fic': order.profisc_fic,
                'profisc_eic': order.profisc_eic,
                'profisc_qr_code': order.profisc_qr_code,
                'profisc_status_control': order.profisc_status_control,
                'profisc_fisc_status_sale': order.profisc_fisc_status,
                'profisc_fic_error_code': order.profisc_fic_error_code,
                'profisc_fic_error_description': order.profisc_fic_error_description,
                'profisc_ubl_id': order.profisc_ubl_id
            })

            _logger.info(
                f"Method _create_invoice is called invoice.profisc_iic::{invoice.profisc_iic}, order.profisc_iic::{order.profisc_iic}")

        # Return the modified invoice
        return invoice

    def _force_create_invoice(self, order):  # Match original signature
        # Call super to get the original functionality for creating an invoice

        # invoice = super(PosOrder, self)._create_invoice(move_vals)

        _logger.info("Calling method _force_create_invoice")
        _logger.info(f"_force_create_invoice:: working with id={order.id}")
        if order.to_invoice:
            _logger.info(f"_force_create_invoice:: working with id={order.id} is ready for creating invoice")
            invoice = self.env['account.move'].search(
                [('id', '=', order.account_move.id)], limit=1)

            _logger.info("Method _force_create_invoice is called %id" % invoice.id)
            invoice.write({
                'profisc_iic': order.profisc_iic,
                'profisc_fic': order.profisc_fic,
                'profisc_eic': order.profisc_eic,
                'profisc_qr_code': order.profisc_qr_code,
                'profisc_status_control': order.profisc_status_control,
                'profisc_fisc_status_sale': order.profisc_fisc_status,
                'profisc_fic_error_code': order.profisc_fic_error_code,
                'profisc_fic_error_description': order.profisc_fic_error_description,
                'profisc_ubl_id': order.profisc_ubl_id
            })

            _logger.info(
                f"Updated values invoice.profisc_iic::{invoice.profisc_iic}, order"
                f".profisc_iic::{order.profisc_iic}")
            return invoice
        else:
            _logger.info(
                "The param 'to_invoice' must be checked in order to create invoice for Order with id=%s",
                order.id)
            return None

    def set_sub_seq(self, invoice_json):
        company = self.env['profisc.auth'].get_current_company()
        if company.profisc_auto_subseq:
            invoice_date_string = invoice_json['date']
            issue_date = datetime.strptime(invoice_date_string, '%d/%m/%Y %H:%M:%S')
            days_difference = get_difference_in_days(issue_date)
            subseq = None
            if days_difference > 0:
                today_dt = datetime.now()
                if days_difference < 2:
                    subseq = "SERVICE"
                elif days_difference <= 10:
                    subseq = "BOUNDBOOK"
                else:
                    if (today_dt.year == issue_date.year and
                            (today_dt.month == issue_date.month or
                             (today_dt.month - issue_date.month) <= 1 and today_dt.day <= 10)):
                        subseq = "NOINTERNET"
                    elif (today_dt.year - issue_date.year == 1 and
                          today_dt.month == 1 and issue_date.month == 12 and today_dt.day <= 10):
                        subseq = "NOINTERNET"
                if subseq:
                    invoice_json['subseq'] = subseq

        return invoice_json
