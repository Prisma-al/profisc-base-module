import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
class AccountMoveReversalExtension(models.TransientModel):

    _inherit = "account.move.reversal"

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        _logger.info(f"prepare values extended::")
        res.update({
            'profisc_isFiscalized' : False,
            'profisc_fic' : None,
            'profisc_iic' : None,
            'profisc_eic' : None,
            'profisc_qr_code' : None,
            'profisc_qr_code_check' : None,
            'profisc_fisc_downloaded' : False,
            'profisc_einvoice_downloaded' : False,
            'profisc_fic_error_code' : None,
            'profisc_fic_error_description' : None,
            'profisc_eic_error_code' : None,
            'profisc_eic_error_description' : None,
            'profisc_fisc_status_sale' : None,
            'profisc_profile_id': 'P10',
            'profisc_invoice_type': '384',
            'profisc_reference_invoice_iic': move.profisc_iic if move.profisc_iic else None,
            'profisc_reference_invoice_date': move.invoice_date if move.invoice_date else None,
            'profisc_status_control': '0',
            'invoice_payment_term_id': move.invoice_payment_term_id.id if move.invoice_payment_term_id else None,
        })
        return res

    def reverse_moves(self, is_modify=False):

        action = super().reverse_moves(is_modify)

        move = self.env['account.move'].search([('id', '=',action['res_id'])])

        move.profisc_isFiscalized = False
        move.profisc_fisc_status = None
        move.profisc_fic = None
        move.profisc_iic = None
        move.profisc_eic = None
        move.profisc_qr_code = None
        move.profisc_qr_code_check = None
        move.profisc_fisc_downloaded = False
        move.profisc_einvoice_downloaded = False
        move.profisc_fic_error_code = None
        move.profisc_fic_error_description = None
        move.profisc_eic_error_code = None
        move.profisc_eic_error_description = None
        move.profisc_fisc_status_sale = None
        move.profisc_status_control = '0'
        return action

