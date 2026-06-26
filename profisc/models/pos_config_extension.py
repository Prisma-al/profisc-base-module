from odoo import models, fields
from lxml import etree

class PosConfig(models.Model):
    _inherit = 'pos.config'

    tcr_code = fields.Selection(selection='_get_tcr_list', string='TCR')
    bu_code = fields.Selection(selection='_get_business_units', string='Business Unit')
    max_pos_payment_amount = fields.Float(string="Vlera maksimale", help="Vendosni vleren maksimale ne Lek")

    # funksioni per te bere te mundur marrjen nga python ne js
    def _get_max_pos_value(self):
        record = self.env['pos.config'].search([], limit=1)
        if record:
            return record.max_pos_payment_amount
        else:
            return False

    def _get_business_units(self):
        bus = self.env['profisc.business_units'].search([('company_id', '=', self.env.company.id)])
        return [(bu.code, bu.code) for bu in bus]

    def _get_tcr_list(self):
        bus = self.env['profisc.tcr'].search([('company_id', '=', self.env.company.id)])
        return [(bu.code, bu.code) for bu in bus]
