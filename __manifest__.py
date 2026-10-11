# -*- coding: utf-8 -*-
{
    'name': 'Elevator Company Operations (Multi-Company)',
    'version': '19.0.1.0.0',
    'category': 'Operations/Field Service',
    'summary': 'Multi-company elevator sales, subcontracted work orders, stage gating, document approvals, and maintenance contracts',
    'description': """
Elevator Operations & Multi-Company Workflow
============================================
Specifically designed for elevator enterprises operating across multiple legal entities:
- **Sales Companies (Company A, etc.)**: Sell elevator units, parts, and 1-year free service contracts to customers ($20k+ packages).
- **Operations Company (Company B)**: Receives subcontracted work orders ($15k internal budget) without redundant sales orders.
- **Site Material Coordination**: Company B technicians arrive on-site and access inventory delivered directly from Company A delivery orders.
- **Stage Gating with Document Uploads**: Technicians and contractors must upload signed checklists, test sheets, and inspection photos before advancing to the next stage.
- **Contractor Payment & Vendor Bills**: Automatic creation of Vendor Bills with custom labels for external contractors upon approved work stages.
- **Handover & Return Notification**: Automatically updates Company A sales orders when installation finishes and activates the 1-year free warranty support contract.
- **Support & Maintenance Contracts**: Periodic visits, inspection work orders, and seamless material requisition from Company A storage.
    """,
    'author': 'Elevator Operations Solutions',
    'depends': [
        'base',
        'sale_management',
        'stock',
        'account',
        'mail',
        'uom',
    ],
    'data': [
        # Security
        'security/elevator_security.xml',
        'security/ir.model.access.csv',
        'security/elevator_rules.xml',
        # Sequences & Master Data
        'data/ir_sequence_data.xml',
        'data/elevator_stage_data.xml',
        # Views
        'views/elevator_site_views.xml',
        'views/elevator_unit_views.xml',
        'views/elevator_work_order_stage_views.xml',
        'views/elevator_work_order_views.xml',
        'views/elevator_contract_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/elevator_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
