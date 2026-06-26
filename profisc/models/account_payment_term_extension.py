from odoo import api, fields, models


class AccountPaymentTermExtension(models.Model):
    _inherit = ['account.payment.term']

    profisc_payment_code = fields.Char(string='Code')
    profisc_payment_code_description = fields.Char(string='Code Description')
