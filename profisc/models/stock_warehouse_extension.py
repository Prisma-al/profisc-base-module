from odoo import _, api, fields, models


class StockWarehouseExtension(models.Model):
    _inherit = 'stock.warehouse'

    profisc_start_point = fields.Selection(
        [
            ("WAREHOUSE", "Warehouse"),
            ("EXHIBITION", "Exhibition"),
            ("STORE", "Store"),
            ("SALE", "Point of Sale"),
            ("ANOTHER", "Another Person's warehouse"),
            ("CUSTOMS", "Customs Warehouse"),
            ("OTHER", "Other"),
        ],
        string='Start Point', default='WAREHOUSE')
