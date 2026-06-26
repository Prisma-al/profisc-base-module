from odoo import api, fields, models


class HrEmployeePrivateExtension(models.Model):
    _inherit = 'hr.employee'

    profisc_operator_code = fields.Char(string='Operator Code')


class HrEmployeePublicExtension(models.Model):
    _inherit = 'hr.employee.public'

    profisc_operator_code = fields.Char(string='Operator Code')
