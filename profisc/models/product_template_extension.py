from odoo import api, fields, models


class ProfiscProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_available_in_pos = fields.Float(compute='_compute_qty_available_in_pos')

    def _compute_qty_available_in_pos(self):
        for product in self:
            # Assuming the POS is linked to a single stock location
            stock_quant = self.env['stock.quant'].search([
                ('location_id', '=',
                 self.env['stock.location'].search([('name', '=', 'Your Store Location Name')], limit=1).id),
                ('product_id', '=', product.id),
            ], limit=1)
            product.qty_available_in_pos = stock_quant.quantity
