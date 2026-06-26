from odoo import api, fields, models


class UomUomExtension(models.Model):
    _inherit = ['uom.uom']

    # profisc_uom_val = fields.Char(string='Profisc Value')
    profisc_uom_val = fields.Many2one('profisc.uoms', string='Profisc Value')
