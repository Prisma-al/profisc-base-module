from odoo import api, fields, models


class ProUoms(models.Model):
    _name = 'profisc.uoms'
    _description = 'uom_imported_from_profisc'

    name = fields.Char(string="Emri i njesise")
    code = fields.Char(string="Kodi i njesise")
    is_active = fields.Boolean(string="Aktive")
