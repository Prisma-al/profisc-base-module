from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    profisc_payment_method = fields.Many2one('profisc.payment_methods', string='Profisc method')
