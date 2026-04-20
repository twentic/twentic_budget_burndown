import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Threshold above which the confirmation wizard is triggered (%)
BUDGET_WARNING_THRESHOLD = 90.0


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ------------------------------------------------------------------
    # Computed budget fields
    # ------------------------------------------------------------------

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
    )
    budget_total = fields.Monetary(
        string='Budget Total',
        currency_field='company_currency_id',
        compute='_compute_budget_progress',
        store=False,
        help='Sum of budgeted amounts for all analytic budget lines linked to this order.',
    )
    budget_spent = fields.Monetary(
        string='Budget Committed',
        currency_field='company_currency_id',
        compute='_compute_budget_progress',
        store=False,
        help=(
            'Already committed amount (billed + confirmed POs) from the '
            'linked analytic budget lines, excluding this order when still in draft.'
        ),
    )
    budget_progress = fields.Float(
        string='Budget Progress (%)',
        compute='_compute_budget_progress',
        store=False,
        digits=(5, 2),
        help=(
            'Percentage of the analytic budget consumed including the current '
            'purchase order amount.'
        ),
    )
    is_over_budget = fields.Boolean(
        string='Over Budget',
        compute='_compute_budget_progress',
        store=False,
        help='True when confirming this order would exceed the available analytic budget.',
    )

    # ------------------------------------------------------------------
    # Budget line lookup — bypasses intermediate computed fields
    # ------------------------------------------------------------------

    def _get_matching_budget_lines(self):
        """Search budget.line records that match this order's analytic distribution and date.

        We search directly from ``analytic_distribution`` (a plain JSON field)
        rather than going through ``order_line.budget_line_ids``.  That computed
        O2M on purchase.order.line depends on ``analytic_json`` (a *stored*
        computed field), which is not written for unsaved records during an
        onchange evaluation.  The direct search avoids that dependency chain and
        makes the progress bar reactive while the user is still editing lines.
        """
        self.ensure_one()
        if not self.date_order:
            return self.env['budget.line']

        order_date = (
            self.date_order.date()
            if hasattr(self.date_order, 'date')
            else self.date_order
        )

        # Collect unique analytic account IDs from all order lines
        analytic_ids = []
        seen = set()
        for line in self.order_line:
            if line.display_type or not line.analytic_distribution:
                continue
            for ids_str in line.analytic_distribution:
                for raw_id in ids_str.split(','):
                    try:
                        aid = int(raw_id.strip())
                        if aid not in seen:
                            analytic_ids.append(aid)
                            seen.add(aid)
                    except (ValueError, TypeError):
                        pass

        if not analytic_ids:
            return self.env['budget.line']

        # ``auto_account_id`` is a stored Many2one on budget.line added by
        # account_budget via analytic.plan.fields.mixin.  It is the inverse
        # field of account.analytic.account.budget_line_ids and is searchable.
        return self.env['budget.line'].search([
            ('auto_account_id', 'in', analytic_ids),
            ('date_from', '<=', order_date),
            ('date_to', '>=', order_date),
            ('budget_analytic_state', '=', 'confirmed'),
            ('budget_analytic_id.budget_type', '!=', 'revenue'),
        ])

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    @api.depends(
        'order_line.analytic_distribution',
        'order_line.price_unit',
        'order_line.product_qty',
        'order_line.qty_invoiced',
        'order_line.display_type',
        'date_order',
        'state',
    )
    def _compute_budget_progress(self):
        for order in self:
            budget_lines = order._get_matching_budget_lines()

            if not budget_lines:
                order.budget_total = 0.0
                order.budget_spent = 0.0
                order.budget_progress = 0.0
                order.is_over_budget = False
                continue

            budget_total = sum(budget_lines.mapped('budget_amount'))
            # committed_amount reflects all confirmed POs + vendor bills
            # for this analytic account as computed by budget.report.
            budget_spent = sum(budget_lines.mapped('committed_amount'))

            # When the order is not yet confirmed its own amount is absent
            # from committed_amount.  Add the pending amount so the bar
            # shows the projected impact of confirming this order.
            pending_amount = 0.0
            if order.state not in ('purchase', 'done'):
                pending_amount = sum(
                    line.price_unit * (line.product_qty - line.qty_invoiced)
                    for line in order.order_line
                    if line.analytic_distribution and not line.display_type
                )

            total_with_pending = budget_spent + pending_amount
            order.budget_total = budget_total
            order.budget_spent = budget_spent
            order.budget_progress = (
                min(100.0, (total_with_pending / budget_total) * 100.0)
                if budget_total > 0
                else 0.0
            )
            order.is_over_budget = total_with_pending > budget_total

            if order.is_over_budget:
                _logger.info(
                    'Purchase order %s would exceed analytic budget '
                    '(%.2f / %.2f — %.1f%%)',
                    order.name,
                    total_with_pending,
                    budget_total,
                    order.budget_progress,
                )

    # ------------------------------------------------------------------
    # Confirm button override — budget warning wizard
    # ------------------------------------------------------------------

    def button_confirm(self):
        """Intercept single-record confirmation when budget threshold is reached."""
        if (
            len(self) == 1
            and self.budget_progress >= BUDGET_WARNING_THRESHOLD
            and not self.env.context.get('skip_budget_warning')
        ):
            return self._action_open_budget_warning()
        return super().button_confirm()

    def _action_open_budget_warning(self):
        """Create and open the budget warning wizard."""
        self.ensure_one()
        wizard = self.env['purchase.budget.warning'].create({
            'purchase_order_id': self.id,
            'budget_progress': self.budget_progress,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Warning'),
            'res_model': 'purchase.budget.warning',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
