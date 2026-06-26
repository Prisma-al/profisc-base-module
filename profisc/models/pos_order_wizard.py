from odoo import models, fields, api
from odoo.exceptions import UserError


class ProfiscInvoiceWizard(models.TransientModel):
    _name = 'profisc.pos_order_wizard'
    _description = 'Profisc pos_order_wizard'

    invoice_subseq = fields.Selection([
        ('n_a', 'Select'),
        ('NOINTERNET', 'No internet'),
        ('BOUNDBOOK', 'Boundbook'),
        ('SERVICE', 'Service'),
        ('TECHNICALERROR', 'Technical Error')
    ], string='Subseq Type', required=True, default='n_a')

    result = fields.Text('Result')

    def action_confirm(self):
        active_ids = self._context.get('active_ids')
        if not active_ids:
            raise UserError("Nuk u gjeten fatura per ridergim")

        result = self.env['pos.order'].profisc_resend(
            self.invoice_subseq,
            active_ids
        )

        self.result = result
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'profisc.pos_order_wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
