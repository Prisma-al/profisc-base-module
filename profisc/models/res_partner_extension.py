from odoo import api, fields, models


class ResPartnerExtension(models.Model):
    _inherit = ['res.partner']

    profisc_customer_vat_type = fields.Selection([
        ('ID', 'ID'),
        ('9923', 'NUIS'),
        ('VAT', 'VAT '),
    ], string='Customer Vat Type', default='ID')

    def get_tax_payer(self):
        return self.env['profisc.api.helper'].getTaxPayer(self.vat)

    def update_tax_payer(self):
        res = self.get_tax_payer()
        if res['status']:
            self.write({'name': res['content'][0].name, 'profisc_customer_vat_type': '9923'})
        return res
