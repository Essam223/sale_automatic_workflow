{
    'name': 'Sale Automatic Workflow',
    'version': '12.0.1.0.0',
    'category': 'Sales Management',
    'license': 'AGPL-3',
    'author': "Akretion, "
              "Camptocamp, "
              "Sodexis, "
              "Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/sale-workflow',
    'depends': [
        'sale_stock',
        # 'sales_team',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        # 'views/sale_workflow_process_view.xml',
        # 'data/automatic_workflow_data.xml',
    ],
}
