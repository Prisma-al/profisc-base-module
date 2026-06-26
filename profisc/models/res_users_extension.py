from odoo import api, fields, models


class ResUsersExtension(models.Model):
    _inherit = ['res.users']

    profisc_operator_code = fields.Char(string='Operator Code')
