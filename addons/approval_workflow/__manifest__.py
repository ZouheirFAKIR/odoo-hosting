# -*- coding: utf-8 -*-

{
    'name': "Moteur de workflow d'approbation",
    'version': '18.0.1.0.0',
    'summary': "Moteur de workflow d'approbation générique et configurable",
    'description': """
Moteur de workflow d'approbation
=================================

Gestion générique des workflows d'approbation pour Odoo Community 18.

Fonctionnalités :
- Catégories d'approbation
- Workflows configurables
- Approbation séquentielle et parallèle
- Étapes d'approbation multiples
- Approbateurs utilisateur/groupe/manager
- Demandes d'approbation
- Historique des approbations
- Piste d'audit
- Tableau de bord et indicateurs clés
    """,

    'author': 'Yealead',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Human Resources/Approvals',

    'depends': [
        'base',
        'mail',
        'hr',
        'product',
        'sale',
        'purchase',
        'stock',
        'hr_holidays',
        'hr_expense',
        'website_slides',
    ],

    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Technical data
        'data/sequence.xml',

        # Modèles d'email de notification (demande en attente / approuvée /
        # refusée) — requis par les méthodes de notification de
        # models/approval_request.py.
        'data/mail_template.xml',

        # Catégories, workflows, étapes et règles métier (toujours
        # chargés, pas seulement en démo — nécessaires pour l'intégration
        # avec les documents métier réels comme sale.order -> approval.request).
        'data/categories_business.xml',

        # Tableau de bord
        'views/approval_dashboard_views.xml',

        # Demandes
        'views/approval_request_views.xml',

        # Configuration
        'views/approval_category_views.xml',
        'views/approval_workflow_views.xml',
        'views/approval_stage_views.xml',
        'views/approval_rule_views.xml',

        # Menus
        'views/approval_menu.xml',

        # Intégration avec les documents métier (sale.order -> approval.request,
        # etc.)
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/hr_expense_views.xml',
        'views/hr_leave_views.xml',
        'views/stock_picking_views.xml',
        'views/slide_channel_views.xml',
    ],

    'demo': [
        'data/demo.xml',
        'data/demo_six_categories.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'approval_workflow/static/src/css/approval_dashboard.css',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}