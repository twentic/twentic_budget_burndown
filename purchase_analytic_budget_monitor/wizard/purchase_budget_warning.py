from odoo import api, fields, models, _


class PurchaseBudgetWarning(models.TransientModel):
    _name = 'purchase.budget.warning'
    _description = 'Purchase Order Budget Warning'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        readonly=True,
    )
    budget_progress = fields.Float(
        string='Budget Progress (%)',
        readonly=True,
        digits=(5, 2),
    )
    warning_message = fields.Char(
        string='Warning Message',
        compute='_compute_warning_message',
    )

    @api.depends('budget_progress', 'purchase_order_id')
    def _compute_warning_message(self):
        for wizard in self:
            wizard.warning_message = _(
                'The analytic budget for this purchase order will reach '
                '%(progress).1f%% after confirmation. '
                'Do you want to continue?',
                progress=wizard.budget_progress,
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Confirm the purchase order bypassing the budget warning check."""
        self.ensure_one()
        return self.purchase_order_id.with_context(
            skip_budget_warning=True,
        ).button_confirm()

    def action_cancel(self):
        """Discard — close the wizard without confirming the order."""
        return {'type': 'ir.actions.act_window_close'}
