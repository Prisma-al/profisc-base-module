from odoo import api, fields, models


class ProfiscPmtMethods(models.Model):
    _name = 'profisc.payment_methods'
    _description = 'List of all payment methods'

    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
    label = fields.Char(string='Label')
    type = fields.Selection([
        ('0', 'All'),
        ('1', 'Cash'),
        ('2', 'Non Cash '),
    ], string='Type', default='1')
