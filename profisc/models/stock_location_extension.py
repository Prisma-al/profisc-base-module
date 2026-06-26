import json
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime


class StockLocationExtension(models.Model):
    _inherit = 'stock.location'

    bu_id = fields.Many2one('profisc.business_units', string='Business Unit')
    tcr_id = fields.Many2one('profisc.tcr', string='Tcr')
