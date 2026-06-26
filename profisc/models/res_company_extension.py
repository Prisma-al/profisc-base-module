from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCompanyExtension(models.Model):
    _inherit = 'res.company'

    profisc_company_id = fields.Char("Company id", default="1")
    profisc_login_endpoint = fields.Char("Login endpoint", default="/public/authenticate")
    profisc_username = fields.Char("Username", default="bsholla")
    profisc_password = fields.Char("Password", default="Test1235?!")
    profisc_search_endpoint = fields.Char("Search endpoint", default="/apiEndpoint/search")
    profisc_upload_invoice = fields.Char("Upload invoice", default="/agent/upload/invoice/V2")
    profisc_upload_wtn_invoice = fields.Char("Upload wtn invoice", default="/agent/upload/wtn")
    profisc_cash_deposit = fields.Char("Register Cash Deposit", default="/agent/cashDeposit")
    profisc_login_token = fields.Char("Login token", default="")
    profisc_auto_subseq = fields.Boolean(string='Auto subseq', default=False)
    profisc_manual_fisc_select = fields.Boolean(string='Manual fisc select', default=False)
    profisc_invoiceStatus = fields.Char("Status Change Api", default="/endpoint/v2/changePurchaseInvoicesStatusInGroup")
    profisc_checkStatus = fields.Char("Check Status Api", default="/apiEndpoint/search")
    profisc_auto_search_nuis = fields.Boolean(string='Auto Search NUIS', default=False)

    profisc_api_endpoint = fields.Selection([
        ('https://demoapi.profisc.al', 'demo'),
        ('https://onlineapi.profisc.al', 'online'),
        ('https://api.profisc.al', 'portal'),
        ('https://devapi.profisc.al', 'dev'),
    ], string='Server', default='https://demoapi.profisc.al')

    profisc_purch_inv_check_time_s = fields.Integer(string='Check for new Invoices time(s)', default=3600)
    # profisc_rate_indicator = fields.Char("Manual Currency Rate", default="1")

    is_in_vat = fields.Boolean(string="Is in Vat", default=True)
    tax_type = fields.Char(
        string="Tax Type",
        compute="_compute_tax_type",
        store=True
    )

    def get_current_company(self):
        res = self.env['profisc.actions'].getTaxPayer(self.vat)
        raise UserError(f"Current Company::{res['content'][0]}")

    @api.depends('is_in_vat')
    def _compute_tax_type(self):
        for company in self:
            company.tax_type = "Normal" if company.is_in_vat else "Fre"