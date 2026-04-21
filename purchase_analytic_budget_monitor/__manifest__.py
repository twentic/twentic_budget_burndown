{
    'name': 'Purchase Analytic Budget Monitor',
    'version': '18.0.1.0.0',
    'author': 'TwenTIC',
    'website': 'https://www.twentic.com',
    'summary': 'Visual budget progress bar on Purchase Orders against Analytic Budgets',
    'description': """
        Extends purchase.order with computed budget metrics (total, spent,
        progress %) based on the active analytic budget lines linked to the
        order's analytic distribution.  Shows a dynamic progress bar on the
        form view and triggers a confirmation wizard when the budget is about
        to be exceeded.
    """,
    'category': 'Purchase',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'account_budget',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_budget_warning_views.xml',
        'views/purchase_order_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
