import logging
from odoo import api, fields, _, models


class ProfiscEinvoiceProfiles(models.Model):
    _name = 'profisc.einvoice_profiles'
    _description = 'List of einvoice profiles'

    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
