import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountTaxExtension(models.Model):
    _inherit = ['account.tax']

    profisc_tax_exempt_reason = fields.Selection(
        [('EXPORT_OF_GOODS', 'EXPORT_OF_GOODS'), ('TAX_FREE', 'TAX_FREE'), ('TYPE_1', 'TYPE_1'), ('TYPE_2', 'TYPE_2'),
         ('MARGIN_SCHEME', 'MARGIN_SCHEME')],
        string='CIS Type', store=True)

    profisc_vat_exempt = fields.Char(string='VAT Exempt')

    profisc_vat_schema = fields.Selection([
        ('normal', 'Normal - S'), ('excluded', 'Excluded - E'), ('fre', 'Fre O'), ('withoutvat', 'Without Vat - Z')
    ])

    included_on_books = fields.Boolean(string='Included On Books', default=False, store=True)

    sale_book_label = fields.Selection(
        [('Shitjet e përjashtuara', 'Shitjet e përjashtuara'), ('Furnizime me 0%', 'Furnizime me 0%'),
         ('Eksporte mallrash', 'Eksporte mallrash'), ('Shitje me shkallë 20%', 'Shitje me shkallë 20%'),
         ('Shitje me shkallë 10%', 'Shitje me shkallë 10%'), ('Shitje me shkallë 6%', 'Shitje me shkallë 6%'),
         ('Autongarkesë TVSH në shitje', 'Autongarkesë TVSH në shitje'), ('Borxh i keq', 'Borxh i keq'),
         ('Shitjet pa TVSH', 'Shitjet pa TVSH'), (
         'Shitje regjimi agjentëve të udhëtimit/ marzhi fitimit /shitje në ankand',
         'Shitje regjimi agjentëve të udhëtimit/ marzhi fitimit /shitje në ankand')],
        string='Sale Book Label', store=True)

    purchase_book_label = fields.Selection(
        [('Të përjashtuara,me Tvsh jo të zbritshme/pa tvsh', 'Të përjashtuara,me Tvsh jo të zbritshme/pa tvsh'),
         ('Blerje investime  brenda vendit pa TVSH', 'Blerje investime  brenda vendit pa TVSH'),
         ('Importe të përjashtuara  të investimit pa TVSH', 'Importe të përjashtuara  të investimit pa TVSH'),
         ('Import mallra  të përjashtuara', 'Import mallra  të përjashtuara'),
         ('Importe mallra me shkallë 20%', 'Importe mallra me shkallë 20%'),
         ('Importe mallra me shkallë 10%', 'Importe mallra me shkallë 10%'),
         ('Importe mallra me shkallë 6%', 'Importe mallra me shkallë 6%'),
         ('Importe të investimit me shkallë 20%', 'Importe të investimit me shkallë 20%'),
         ('Nga Furnitorë Vendas me shkalle 20%', 'Nga Furnitorë Vendas me shkalle 20%'),
         ('Nga Furnitorë Vendas me shkallë 10%', 'Nga Furnitorë Vendas me shkallë 10%'),
         ('Nga Furnitorë Vendas me shkallë 6%', 'Nga Furnitorë Vendas me shkallë 6%'),
         ('Të Investimit nga Furnitorë Vendas me shkallë 20%', 'Të Investimit nga Furnitorë Vendas me shkallë 20%'),
         ('Nga Fermerët vendas', 'Nga Fermerët vendas'),
         ('Autongarkesë TVSH në blerje me të drejtë kreditimi', 'Autongarkesë TVSH në blerje me të drejtë kreditimi'),
         ('Rregullime të TVSH-së së zbritshme', 'Rregullime të TVSH-së së zbritshme'),
         ('Veprime të borxhit të keq', 'Veprime të borxhit të keq')],string='Purchase Book Label', store=True)
