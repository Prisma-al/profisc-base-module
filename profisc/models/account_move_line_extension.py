from odoo import api, fields, models

class AccountMoveLinesExtension(models.Model):
    _inherit = ['account.move.line']
    _name = "account.move.line"

    profisc_uom = fields.Many2one('profisc.uoms', string="Unit of Measure", default=None)