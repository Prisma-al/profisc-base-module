import json
import logging
import re
from datetime import date

import requests
import textwrap

from odoo import api, fields, models, _

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class AccountMoveExtension(models.Model):
    _inherit = 'account.move'
    _name = 'account.move'


    profisc_cis_type = fields.Selection([('0', 'No Fiscalization'), ('-1', 'Fiscalization'), ('1', 'E-invoice')],
                                        store=True, string='Cis Type', default='0')
    profisc_fisc_status = fields.Selection(
        [("DELIVERED", "DELIVERED"), ("ACCEPTED", "ACCEPTED"), ("REFUSED", "REFUSED"),
         ("PARTIALLY_PAID", "PARTIALLY PAID"), ("PAID", "PAID"), ("OVERPAID", "OVERPAID")], string='Cis Status',
        deafult=None, tracking=True)
    profisc_fisc_status_sale = fields.Char(string='Cis Sale Status', default=None)
    profisc_iic = fields.Char(string='IIC')
    profisc_fic = fields.Char(string='FIC')
    profisc_eic = fields.Char(string='EIC', default=None)
    profisc_qr_code = fields.Char(string='Qr Url')
    profisc_qr_code_check = fields.Binary(string='Qr Code', attachment=True)
    profisc_fisc_downloaded = fields.Boolean(string='Fiscal Downloaded')
    profisc_einvoice_downloaded = fields.Boolean(string='E-Invoice Downloaded', default=None)
    profisc_fic_error_code = fields.Char(string='FIC Error Code')
    profisc_fic_error_description = fields.Char(string='FIC Error Description')
    profisc_eic_error_code = fields.Char(string='EIC Error Code')
    profisc_eic_error_description = fields.Char(string='EIC Error Description')
    profisc_ubl_id = fields.Char(string='UBL ID')
    profisc_purchaseBill_id = fields.Integer(string='Purchase Bill ID', default=None)
    profisc_isEinvoice = fields.Boolean(string='Fiscal Downloaded')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    profisc_currency_rate = fields.Char(compute='_generate_rate', string='Kursi ne CIS', default=1.00)
    amount_total_unsigned = fields.Monetary(string='Total (TVSH Included)', store=True, readonly=True, compute='_compute_amount_total_unsigned', currency_field='company_currency_id')

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id', store=True, readonly=False, precompute=True,
        required=False,
        states={'draft': [('readonly', False)]},
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )

    profisc_invoice_type = fields.Selection(
        [('380', 'Fature tregtare'),
         ('384', 'Fature korrektive'),
         ('386', 'Fature parapagimi'),
         ('389', 'Fature vete-faturimi'),
         ('388', 'Fature tatimore'),
         ('395', 'Fature e ngarkeses'),
         ('393', 'Fature e faktorizuar'),
         ('575', 'Fature e siguruesit'),
         ('383', 'Note debiti'),
         ('80', 'Note debiti te lidhura me mallrat dhe sherbimet'),
         ('84', 'Note debiti te lidhura me rregullimet financiare'),
         ('623', 'Fature e dergeses') ],
        string='Invoice Type', store=True, )

    profisc_tcr_code = fields.Selection(selection='_get_tcr_list', string='TCR Code')
    # , default='qh707fm959')

    # profisc_bu_code = fields.Selection([
    #     ('cs862wh907', 'Tetra PRO - Tirane, Kompleksi KIKA 2, Rruga "Tish Daija", kati i dyte, godina Nr.7, '
    #                    'njesia Bashkiake Nr.5, Tirane'),
    # ], store=True, string='Bu Code')

    # profisc_tcr_code = fields.Selection(selection='_get_tcr_list', string='TCR')
    profisc_bu_code = fields.Selection(selection='_get_business_units', string='Business Unit')
    # , default='cs862wh907')

    profisc_status_control = fields.Selection([('0', 'In Process'), ('2', 'Error'), ('3', 'Success'), ], store=True,
                                              string='Status Control')

    profisc_profile_id = fields.Selection([
        ('P1', 'P1 - Faturimi i furnizimit te mallrave dhe shërbimeve te porositura ne baze te kontrates'),
        ('P2', 'P2 - Faturimi periodik i dorezimit te bazuar në kontrate'),
        ('P3', 'P3 - Dorëzimi i faturimit mbi porosi te paparashikuara'),
        ('P4', 'P4 - Pagesa paraprake'),
        ('P5', 'P5 - Pagesa né vend'),
        ('P6', 'P6 - Pagesa para dorëzimit bazuar në njé porosi blerjeje'),
        ('P7', 'P7 - Faturat në lidhje me nje shenim transporti'),
        ('P8', 'P8 - Faturat ne lidhje me një shënim transporti dhe deftese'),
        ('P9', 'P9 - Miratimi ose faturimi negativ'),
        ('P10', 'P10 - Faturimi korrigjues'),
        ('P11', 'P11 - Faturim i pjesshem dhe perfundimtar'),
        ('P12', 'P12 - Vetefaturim'),
    ], store=True, string='Profile ID', default='P1')

    profisc_subseq = fields.Selection([
        ('NOINTERNET', 'NO INTERNET'),
        ('SERVICE', 'SERVICE'),
        ('TECHNICALERROR', 'TECHNICAL ERROR'),
        ('BOUNDBOOK', 'BOUNDBOOK'),
    ], store=True, string='Subseq')
    profisc_start_date = fields.Date(string='Start Date')
    profisc_end_date = fields.Date(string='End Date')
    profisc_reference_invoice_date = fields.Date(string='Reference Invoice Date')
    profisc_reference_invoice_iic = fields.Char(string='Reference Invoice IIC')

    profisc_self_invoice_type = fields.Selection([
        ('AGREEMENT', 'AGREEMENT'),
        ('DOMESTIC', 'DOMESTIC'),
        ('ABROAD', 'ABROAD'),
        ('SELF', 'SELF'),
        ('OTHER', 'OTHER'),
    ], store=True, string='Self Invoice Type')
    profisc_reverse_charge = fields.Boolean(string='Reverse Charge')
    profisc_isFiscalized = fields.Boolean(string='Is Fiscalized')

    # Taxes Sale
    profisc_sale_exampted_sales = fields.Monetary(string='Shitjet e përjashtuara', default=0,
                                                  currency_field='company_currency_id')
    profisc_sale_0_on_supply = fields.Monetary(string='Furnizime me 0%', default=0,
                                               currency_field='company_currency_id')
    profisc_sale_without_vat = fields.Monetary(string='Shitjet pa TVSH', default=0,
                                               currency_field='company_currency_id')
    profisc_sale_export = fields.Monetary(string='Eksporte mallrash', default=0, currency_field='company_currency_id')
    profisc_sale_taxable_value_20 = fields.Monetary(string='Shitje me shkallë 20%', default=0,
                                                    currency_field='company_currency_id')
    profisc_sale_vat20 = fields.Monetary(string='TVSH 20%', default=0, currency_field='company_currency_id')
    profisc_sale_taxable_value_10 = fields.Monetary(string='Shitje me shkallë 10%', default=0,
                                                    currency_field='company_currency_id')
    profisc_sale_vat10 = fields.Monetary(string='TVSH 10%', default=0, currency_field='company_currency_id')
    profisc_sale_taxable_value_6 = fields.Monetary(string='Shitje me shkallë 6%', default=0,
                                                   currency_field='company_currency_id')
    profisc_sale_vat6 = fields.Monetary(string='TVSH 6%', default=0, currency_field='company_currency_id')
    profisc_sale_reverse_charge = fields.Monetary(string='Autongarkesë në shitje', default=0,
                                                  currency_field='company_currency_id')
    profisc_sale_reverse_charge_vat = fields.Monetary(string='Autongarkesë TVSH në shitje', default=0,
                                                      currency_field='company_currency_id')
    profisc_sale_bad_debt = fields.Monetary(string='Borxh i keq', default=0, currency_field='company_currency_id')
    profisc_sale_bad_debt_vat = fields.Monetary(string='Borxh i keq TVSH', default=0,
                                                currency_field='company_currency_id')
    profisc_sale_vat0_margin_scheme = fields.Monetary(
        string='Shitje regjimi agjentëve të udhëtimit/ marzhi fitimit /shitje në ankand', default=0,
        currency_field='company_currency_id')

    profisc_sale_vat0_margin_scheme_tvsh = fields.Monetary(
        string='Shitje regjimi agjentëve të udhëtimit/ marzhi fitimit /shitje në ankand TVSH', default=0,
        currency_field='company_currency_id')

    # Taxes Purchase
    profisc_te_perjashtuara = fields.Monetary(string='Të përjashtuara,me Tvsh jo të zbritshme/pa tvsh', default=0,
                                              currency_field='company_currency_id')
    profisc_investime = fields.Monetary(string='Blerje investime  brenda vendit pa TVSH', default=0,
                                        currency_field='company_currency_id')
    profisc_te_perjashtuara_te_investimit = fields.Monetary(string='Importe të përjashtuara  të investimit pa TVSH',
                                                            default=0, currency_field='company_currency_id')
    profisc_import = fields.Monetary(string='Import mallra  të përjashtuara', default=0,
                                     currency_field='company_currency_id')
    profisc_import_20_takse = fields.Monetary(string='Import mallra  me shkalle 20% TVSH', default=0,
                                              currency_field='company_currency_id')
    profisc_import_20 = fields.Monetary(string='Import mallra  me shkalle 20%', default=0,
                                        currency_field='company_currency_id')
    profisc_import_10_takse = fields.Monetary(string='Import mallra  me shkalle 10% TVSH', default=0,
                                              currency_field='company_currency_id')
    profisc_import_10 = fields.Monetary(string='Import mallra  me shkalle 10%', default=0,
                                        currency_field='company_currency_id')
    profisc_import_6_takse = fields.Monetary(string='Import mallra me shkalle 6% TVSH', default=0,
                                             currency_field='company_currency_id')
    profisc_import_6 = fields.Monetary(string='Import mallra me shkalle 6%', default=0,
                                       currency_field='company_currency_id')
    profisc_importe_te_investimit_20_takse = fields.Monetary(string='Importe të investimit me shkallë 20% TVSH',
                                                             default=0, currency_field='company_currency_id')
    profisc_importe_te_investimit_20 = fields.Monetary(string='Importe të investimit me shkallë 20%', default=0,
                                                       currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_20_takse = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 20% TVSH',
                                                            default=0, currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_20 = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 20%', default=0,
                                                      currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_10_takse = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 10% TVSH',
                                                            default=0, currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_10 = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 10%', default=0,
                                                      currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_6_takse = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 6% TVSH', default=0,
                                                           currency_field='company_currency_id')
    profisc_nga_furnitore_vendas_6 = fields.Monetary(string='Nga Furnitorë Vendas me shkalle 6%', default=0,
                                                     currency_field='company_currency_id')
    profisc_te_investimit_nga_furnitore_vendas_20_takse = fields.Monetary(
        string='Të Investimit nga Furnitorë Vendas me shkallë 20% TVSH', default=0,
        currency_field='company_currency_id')
    profisc_te_investimit_nga_furnitore_vendas_20 = fields.Monetary(
        string='Të investimit nga Furnitorë Vendas me shkalle 20%', default=0, currency_field='company_currency_id')
    profisc_fermere_vendas_takse = fields.Monetary(string='Nga Fermerët vendas TVSH', default=0,
                                                   currency_field='company_currency_id')
    profisc_fermere_vendas = fields.Monetary(string='Nga Fermerët vendas', default=0,
                                             currency_field='company_currency_id')
    profisc_autongarkese_takse = fields.Monetary(string='Autongarkesë TVSH në blerje me të drejtë kreditimi TVSH',
                                                 default=0, currency_field='company_currency_id')
    profisc_autongarkese = fields.Monetary(string='Autongarkesë TVSH në blerje me të drejtë kreditimi', default=0,
                                           currency_field='company_currency_id')
    profisc_regullime_takse = fields.Monetary(string='Rregullime të TVSH-së së zbritshme TVSH', default=0,
                                              currency_field='company_currency_id')
    profisc_regullime = fields.Monetary(string='Rregullime të TVSH-së së zbritshme', default=0,
                                        currency_field='company_currency_id')
    profisc_borxh_i_keq_takse = fields.Monetary(string='Veprime të borxhit të keq TVSH', default=0,
                                                currency_field='company_currency_id')
    profisc_borxh_i_keq = fields.Monetary(string='Veprime të borxhit të keq', default=0,
                                          currency_field='company_currency_id')

    #BKT statuses

    profisc_bkt_status = fields.Char(string='BKT Status')
    profisc_bkt_paymentType = fields.Char(string='BKT Payment Type')
    profisc_bkt_amount = fields.Char(string='BKT Paid Amount')
    profisc_bkt_source = fields.Char(string='BKT Source')
    profisc_bkt_paymentMethod = fields.Char(string='BKT Payment Method')

    # def is_sale_invoice(self):
    #     return self.type == 'out_invoice'

    # fusha per te ndryshu due date
    profisc_due_date = fields.Date(string="Due Date", help="This is a date used to change the invoice due date when needed")

    # fusha me dergu ne profisc per p12 - p10 relation
    is_p10_check = fields.Boolean(string="Is P10", default=False,
                                  help="Bool field to determine wether the p12 is actually a corrective inv (P10)", compute="compute_is_p10_check")

    #funksioni me e lon isp10 true ose false nebaze te kushtit
    def compute_is_p10_check(self):
        for rec in self:
            if rec.profisc_profile_id == "P10" and rec.profisc_reference_invoice_iic:
                rec.is_p10_check = True
            else:
                rec.is_p10_check = False

    #funksioni per me e nddryshu due date
    def action_post(self):
        # thrrasim dhe metoden aktuale pa humb asnji funksionalitet
        res = super().action_post()
        for move in self:
            if move.profisc_due_date:
                move.invoice_date_due = move.profisc_due_date
        return res


    # def is_sale_invoice(self):
    #     return self.type == 'out_invoice'

    # ndryshimi by default per inv type
    @api.onchange('profisc_profile_id')
    def check_profile_id(self):
        for move in self:
            if move.profisc_profile_id == "P12":
                move.profisc_invoice_type = "389"

    def _get_business_units(self):
        bus = self.env['profisc.business_units'].search([('company_id', '=', self.env.company.id), ('status', '=', True)])
        return [(bu.code, bu.code) for bu in bus]

    def _get_tcr_list(self):
        tcrs = self.env['profisc.tcr'].search([('company_id', '=', self.env.company.id), ('status', '=', True)])
        return [(tcr.code, tcr.code) for tcr in tcrs]

    def send_to_profisc(self):
        self.env['profisc.api.helper'].sendToProfisc(self.id)

    def get_fisc_pdf(self):
        self.env['profisc.api.helper'].getFiscPdf(self.id)

    def get_e_invoice_pdf(self):
        self.env['profisc.api.helper'].getEinvoicePdf(self.id)

    def get_qr_code(self):
        self.env['profisc.api.helper'].getQrCode(self.id)

    # def open_PurchaseBill(self):
    #     return {
    #         'name': _("Purchase Bills"),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'profisc.purchase_book',
    #         'context': {'create': False},
    #         'view_mode': 'form',
    #         'res_id': self.profisc_purchaseBill_id,
    #     }

    def recalculateTaxes(self):

        invoices = self.env['account.move'].browse(self._context.get('active_ids'))
        for invoice in invoices:
            invoice._compute_taxes()

    def add_attachment_vendorBill(self):

        old_obj = self.env['account.move'].search([('id', '=', self.id)])
        # old_obj_purchase = self.env['profisc.purchase_book'].search([('id', '=', self.profisc_purchaseBill_id)])

        self.env['profisc.actions'].add_attachments_vendorBill(self.profisc_eic, old_obj)
        # self.env['profisc.book_actions'].add_attachments_CisPurchase(self.profisc_eic, old_obj_purchase)

    # def accept_bill(self):
    #     purchBill = self.env['profisc.purchase_book'].search([('id', '=', self.profisc_purchaseBill_id)])
    #     response = self.env['profisc.book_actions'].accept_bills(self.profisc_eic, "ACCEPTED")
    #     res = response.json()
    #     print(res)
    #     if res['status'] == True:
    #         self.profisc_fisc_status = 'ACCEPTED'
    #         purchBill.purch_cis_status = 'ACCEPTED'
    #     else:
    #         raise UserError(_("Veprimi nuk u krye me sukses"))
    #
    # def reject_bill(self):
    #     purchBill = self.env['profisc.purchase_book'].search([('id', '=', self.profisc_purchaseBill_id)])
    #     response = self.env['profisc.book_actions'].accept_bills(self.profisc_eic, "REFUSED")
    #     res = response.json()
    #     if res['status'] == True:
    #         self.profisc_fisc_status = 'REFUSED'
    #         purchBill.purch_cis_status = 'REFUSED'
    #     else:
    #         raise UserError(_("Veprimi nuk u krye me sukses"))
    #
    #
    # def get_BKT_single_status(self):
    #     self.env['profisc.actions'].get_BKT_status(self.profisc_iic, self)

    @api.depends(
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        # 'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state')
    def _compute_amount(self):

        super()._compute_amount()

        self._compute_taxes()

    @api.depends('partner_id')
    def _compute_same_currency(self):
        for record in self:
            print(f"Partner_id Depends:: ", record.partner_id.profisc_sale_exampted_sales)
            record.profisc_sale_exampted_sales_access = record.partner_id.profisc_sale_exampted_sales

    def _compute_taxes(self):

        for move in self:

            profisc_sale_exampted_sales = 0
            profisc_sale_0_on_supply = 0
            profisc_sale_without_vat = 0
            profisc_sale_export = 0
            profisc_sale_taxable_value_20 = 0
            profisc_sale_vat20 = 0
            profisc_sale_taxable_value_10 = 0
            profisc_sale_vat10 = 0
            profisc_sale_taxable_value_6 = 0
            profisc_sale_vat6 = 0
            profisc_sale_reverse_charge = 0
            profisc_sale_reverse_charge_vat = 0
            profisc_sale_bad_debt = 0
            profisc_sale_bad_debt_vat = 0
            profisc_sale_vat0_margin_scheme = 0

            profisc_te_perjashtuara = 0
            profisc_investime = 0
            profisc_te_perjashtuara_te_investimit = 0
            profisc_import = 0
            profisc_import_20_takse = 0
            profisc_import_20 = 0
            profisc_import_10_takse = 0
            profisc_import_10 = 0
            profisc_import_6_takse = 0
            profisc_import_6 = 0
            profisc_importe_te_investimit_20_takse = 0
            profisc_importe_te_investimit_20 = 0
            profisc_nga_furnitore_vendas_20_takse = 0
            profisc_nga_furnitore_vendas_20 = 0
            profisc_nga_furnitore_vendas_10_takse = 0
            profisc_nga_furnitore_vendas_10 = 0
            profisc_nga_furnitore_vendas_6_takse = 0
            profisc_nga_furnitore_vendas_6 = 0
            profisc_te_investimit_nga_furnitore_vendas_20_takse = 0
            profisc_te_investimit_nga_furnitore_vendas_20 = 0
            profisc_fermere_vendas_takse = 0
            profisc_fermere_vendas = 0
            profisc_autongarkese_takse = 0
            profisc_autongarkese = 0
            profisc_regullime_takse = 0
            profisc_regullime = 0
            profisc_borxh_i_keq_takse = 0
            profisc_borxh_i_keq = 0

            if move.invoice_date != False:
                currency_rate = 1.00
                if move.currency_id == move.company_id.currency_id:
                    currency_rate = 1.00
                elif move.amount_total_in_currency_signed != 0:
                    currency_rate = move.amount_total_signed / move.amount_total_in_currency_signed

                _logger.info(f"currency_rate:: {currency_rate} {move.invoice_date}")
                # _logger.info(f"invoice:: {move[0]}")
                # _logger.info(f"invoice:: {move[0].profisc_sale_exampted_sales}")

                if move[0].move_type in ('in_refund', 'out_refund'):
                    coef = -1
                else:
                    coef = 1

                if move[0].move_type in ('out_invoice', 'out_refund'):
                    for line in move.line_ids:
                        if (line.tax_ids.sale_book_label == 'Shitjet e përjashtuara'):
                            profisc_sale_exampted_sales += line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Furnizime me 0%'):
                            profisc_sale_0_on_supply += line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Shitjet pa TVSH'):
                            profisc_sale_without_vat += line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Eksporte mallrash'):
                            profisc_sale_export += line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Shitje me shkallë 20%'):
                            # _logger.info(f"tax amount:: {}")
                            # _logger.info(f"tax:: {profisc_sale_vat20}")
                            profisc_sale_taxable_value_20 += line.price_subtotal * currency_rate
                            profisc_sale_vat20 += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Shitje me shkallë 10%'):
                            profisc_sale_taxable_value_10 += line.price_subtotal * currency_rate
                            profisc_sale_vat10 += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Shitje me shkallë 6%'):
                            profisc_sale_taxable_value_6 += line.price_subtotal * currency_rate
                            profisc_sale_vat6 += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Autongarkesë TVSH në shitje'):
                            profisc_sale_reverse_charge += line.price_subtotal * currency_rate
                            profisc_sale_reverse_charge_vat += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.sale_book_label == 'Borxh i keq'):
                            profisc_sale_bad_debt += line.price_subtotal * currency_rate
                            profisc_sale_bad_debt_vat += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (
                                line.tax_ids.sale_book_label == 'Shitje regjimi agjentëve të udhëtimit/ marzhi fitimit /shitje në ankand'):
                            profisc_sale_vat0_margin_scheme += line.price_subtotal * currency_rate

                    move.profisc_sale_exampted_sales = profisc_sale_exampted_sales * coef
                    move.profisc_sale_0_on_supply = profisc_sale_0_on_supply * coef
                    move.profisc_sale_without_vat = profisc_sale_without_vat * coef
                    move.profisc_sale_export = profisc_sale_export * coef
                    move.profisc_sale_taxable_value_20 = profisc_sale_taxable_value_20 * coef
                    move.profisc_sale_vat20 = profisc_sale_vat20 * coef
                    move.profisc_sale_taxable_value_10 = profisc_sale_taxable_value_10 * coef
                    move.profisc_sale_vat10 = profisc_sale_vat10 * coef
                    move.profisc_sale_taxable_value_6 = profisc_sale_taxable_value_6 * coef
                    move.profisc_sale_vat6 = profisc_sale_vat6 * coef
                    move.profisc_sale_reverse_charge = profisc_sale_reverse_charge * coef
                    move.profisc_sale_reverse_charge_vat = profisc_sale_reverse_charge_vat * coef
                    move.profisc_sale_bad_debt = profisc_sale_bad_debt * coef
                    move.profisc_sale_bad_debt_vat = profisc_sale_bad_debt_vat * coef
                    move.profisc_sale_vat0_margin_scheme = profisc_sale_vat0_margin_scheme * coef


                elif move[0].move_type in ('in_invoice', 'in_refund'):
                    for line in move.line_ids:
                        if (line.tax_ids.purchase_book_label == 'Të përjashtuara,me Tvsh jo të zbritshme/pa tvsh'):
                            profisc_te_perjashtuara += line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Blerje investime  brenda vendit pa TVSH'):
                            profisc_investime += line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Importe të përjashtuara  të investimit pa TVSH'):
                            profisc_te_perjashtuara_te_investimit += line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Import mallra  të përjashtuara'):
                            profisc_import += line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Importe mallra me shkallë 20%'):
                            # _logger.info(f"tax amount:: {}")
                            # _logger.info(f"tax:: {profisc_sale_vat20}")
                            profisc_import_20 += line.price_subtotal * currency_rate
                            profisc_import_20_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Importe mallra me shkallë 10%'):
                            profisc_import_10 += line.price_subtotal * currency_rate
                            profisc_import_10_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Importe mallra me shkallë 6%'):
                            profisc_import_6 += line.price_subtotal * currency_rate
                            profisc_import_6_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Importe të investimit me shkallë 20%'):
                            profisc_importe_te_investimit_20 += line.price_subtotal * currency_rate
                            profisc_importe_te_investimit_20_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Nga Furnitorë Vendas me shkalle 20%'):
                            profisc_nga_furnitore_vendas_20 += line.price_subtotal * currency_rate
                            profisc_nga_furnitore_vendas_20_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Nga Furnitorë Vendas me shkallë 10%'):
                            profisc_nga_furnitore_vendas_10 += line.price_subtotal * currency_rate
                            profisc_nga_furnitore_vendas_10_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Nga Furnitorë Vendas me shkallë 6%'):
                            profisc_nga_furnitore_vendas_6 += line.price_subtotal * currency_rate
                            profisc_nga_furnitore_vendas_6_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Të Investimit nga Furnitorë Vendas me shkallë 20%'):
                            profisc_te_investimit_nga_furnitore_vendas_20 += line.price_subtotal * currency_rate
                            profisc_te_investimit_nga_furnitore_vendas_20_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Nga Fermerët vendas'):
                            profisc_fermere_vendas += line.price_subtotal * currency_rate
                            profisc_fermere_vendas_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Autongarkesë TVSH në blerje me të drejtë kreditimi'):
                            profisc_autongarkese += line.price_subtotal * currency_rate
                            profisc_autongarkese_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Rregullime të TVSH-së së zbritshme'):
                            profisc_regullime += line.price_subtotal * currency_rate
                            profisc_regullime_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate
                        elif (line.tax_ids.purchase_book_label == 'Veprime të borxhit të keq'):
                            profisc_borxh_i_keq += line.price_subtotal * currency_rate
                            profisc_borxh_i_keq_takse += line.price_total * currency_rate - line.price_subtotal * currency_rate

                    move.profisc_te_perjashtuara = profisc_te_perjashtuara * coef
                    move.profisc_investime = profisc_investime * coef
                    move.profisc_te_perjashtuara_te_investimit = profisc_te_perjashtuara_te_investimit * coef
                    move.profisc_import = profisc_import * coef
                    move.profisc_import_20_takse = profisc_import_20_takse * coef
                    move.profisc_import_20 = profisc_import_20 * coef
                    move.profisc_import_10_takse = profisc_import_10_takse * coef
                    move.profisc_import_10 = profisc_import_10 * coef
                    move.profisc_import_6_takse = profisc_import_6_takse * coef
                    move.profisc_import_6 = profisc_import_6 * coef
                    move.profisc_importe_te_investimit_20_takse = profisc_importe_te_investimit_20_takse * coef
                    move.profisc_importe_te_investimit_20 = profisc_importe_te_investimit_20 * coef
                    move.profisc_nga_furnitore_vendas_20_takse = profisc_nga_furnitore_vendas_20_takse * coef
                    move.profisc_nga_furnitore_vendas_20 = profisc_nga_furnitore_vendas_20 * coef
                    move.profisc_nga_furnitore_vendas_10_takse = profisc_nga_furnitore_vendas_10_takse * coef
                    move.profisc_nga_furnitore_vendas_10 = profisc_nga_furnitore_vendas_10 * coef
                    move.profisc_nga_furnitore_vendas_6_takse = profisc_nga_furnitore_vendas_6_takse * coef
                    move.profisc_nga_furnitore_vendas_6 = profisc_nga_furnitore_vendas_6 * coef
                    move.profisc_te_investimit_nga_furnitore_vendas_20_takse = profisc_te_investimit_nga_furnitore_vendas_20_takse * coef
                    move.profisc_te_investimit_nga_furnitore_vendas_20 = profisc_te_investimit_nga_furnitore_vendas_20 * coef
                    move.profisc_fermere_vendas_takse = profisc_fermere_vendas_takse * coef
                    move.profisc_fermere_vendas = profisc_fermere_vendas * coef
                    move.profisc_autongarkese_takse = profisc_autongarkese_takse * coef
                    move.profisc_autongarkese = profisc_autongarkese * coef
                    move.profisc_regullime_takse = profisc_regullime_takse * coef
                    move.profisc_regullime = profisc_regullime * coef
                    move.profisc_borxh_i_keq_takse = profisc_borxh_i_keq_takse * coef
                    move.profisc_borxh_i_keq = profisc_borxh_i_keq * coef

    @api.depends('currency_id')
    def _generate_rate(self):
        currency_rate = 1.00
        for move in self:
            _logger.info(f"@api_depends:: currency_id:: {move.currency_id}")
            if move.currency_id == move.company_id.currency_id:
                currency_rate = 1.00
            elif move.amount_total_in_currency_signed != 0:
                currency_rate = move.amount_total_signed / move.amount_total_in_currency_signed

            move.profisc_currency_rate = currency_rate

    @api.depends('amount_total_signed')
    def _compute_amount_total_unsigned(self):
        for move in self:
            if move.move_type in ('in_invoice', 'out_invoice'):
                move.amount_total_unsigned = abs(move.amount_total_signed)
            else:
                move.amount_total_unsigned = -abs(move.amount_total_signed)

    @api.onchange('profisc_end_date')
    def _change_accounting_date(self):
        for move in self:
            if move.profisc_profile_id == 'P2':
                move.date = move.profisc_end_date

    def correct_invoice(self):

        self.env['profisc.actions'].create_corrective_invoice(self)

    @api.onchange('profisc_profile_id')
    def _onchange_profisc_profile_id(self):
        profile_to_invoice_type = {
            'P1': '388',
            'P2': '388',
            'P3': '388',
            'P4': '386',
            'P10': '384',
            'P12': '389',
        }

        for move in self:
            if move.profisc_profile_id in profile_to_invoice_type:
                move.profisc_invoice_type = profile_to_invoice_type[move.profisc_profile_id]
            else:
                move.profisc_invoice_type = False