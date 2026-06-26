from odoo import api, fields, models


class VehiclePlates(models.Model):
    _name = 'profisc.wtn_vehicles'
    _description = 'List of all vehicles, name and plate'

    name = fields.Char(string='Name')
    plate = fields.Char(string='Plate')
