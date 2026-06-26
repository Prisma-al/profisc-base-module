from odoo import http
from odoo.http import request

class PosCustomController(http.Controller):

    @http.route('/pos/get_bkt_status', type='json', auth='user')
    def custom_action(self, iic, company_id):
        print(iic, company_id)
        order = request.env['pos.order'].search([('profisc_iic', '=', iic)], limit=1)
        if not order:
            return {'error': 'Order not found'}
        return order.get_BKT_status(iic, order, company_id)