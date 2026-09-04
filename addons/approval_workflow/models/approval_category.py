# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = "Catégorie d'approbation"
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        index=True,
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        ondelete='set null',
    )

    request_ids = fields.One2many(
        'approval.request',
        'category_id',
        string='Demandes',
    )

    request_count = fields.Integer(
        string='Demandes',
        compute='_compute_request_count',
    )

    icon = fields.Char(
        string='Icône',
        default='fa-check-square-o',
        help="Classe d'icône Font Awesome affichée sur la carte du "
             "tableau de bord, ex: fa-plane, fa-money, fa-file-text-o, "
             "fa-car, fa-shopping-cart, fa-handshake-o.",
    )

    color = fields.Integer(
        string='Couleur de la carte',
        default=0,
        help="Index de couleur d'accentuation (0-7) utilisé pour le "
             "fond de l'icône sur la carte du tableau de bord.",
    )

    to_review_count = fields.Integer(
        string='À examiner',
        compute='_compute_to_review_count',
        help="Nombre de demandes de cette catégorie actuellement en "
             "attente d'approbation par l'utilisateur connecté.",
    )

    use_product_lines = fields.Boolean(
        string='Nécessite une sélection de produits',
        default=False,
        help="Si coché, les demandes de cette catégorie doivent "
             "sélectionner de vrais produits (depuis le catalogue "
             "produits) plutôt qu'un montant libre. Le montant de la "
             "demande est alors calculé automatiquement à partir des "
             "produits sélectionnés. Exemple : 'Achat' ou 'Achat de "
             "logiciel'.",
    )

    category_type = fields.Selection(
        selection=[
            ('generic', 'Générique'),
            ('purchase', "Demande d'achat"),
            ('sale', 'Validation de commande'),
            ('leave', 'Demande de congé'),
            ('expense', 'Validation de dépense'),
            ('training', 'Demande de formation'),
            ('stock', 'Transfert de stock'),
        ],
        string='Type de catégorie',
        default='generic',
        required=True,
        help="Détermine quels champs métier spécifiques sont affichés "
             "sur le formulaire des demandes de cette catégorie "
             "(achat, congé, dépense, formation, stock...). Le moteur "
             "de workflow (étapes, règles, approbateurs) reste "
             "strictement le même quel que soit ce type : ce champ ne "
             "sert qu'à afficher les bons champs, pas à créer un "
             "second moteur.",
    )

    related_model_id = fields.Many2one(
        'ir.model',
        string='Modèle métier lié',
        help="Modèle Odoo du document métier externe que cette "
             "catégorie fait approuver (ex: sale.order, hr.leave, "
             "hr.expense, stock.picking). Laisser vide si la demande "
             "d'approbation EST elle-même le document (ex: Demande "
             "d'achat, Formation, qui n'ont pas d'équivalent Odoo "
             "Community préexistant).",
    )

    final_action_method = fields.Char(
        string='Méthode déclenchée à l\'approbation finale',
        help="Nom de la méthode Python à appeler sur le document lié "
             "(related_model_id) une fois la demande totalement "
             "approuvée, ex: 'action_confirm'. Laisser vide si "
             "aucune action automatique n'est nécessaire.",
    )

    refusal_action_method = fields.Char(
        string='Méthode déclenchée au refus',
        help="Nom de la méthode Python à appeler sur le document lié "
             "(related_model_id) lorsque la demande est refusée, ex: "
             "'action_awe_refuse'. Laisser vide si aucune action "
             "automatique n'est nécessaire. Symétrique de "
             "final_action_method.",
    )

    _sql_constraints = [
        (
            'code_company_unique',
            'unique(code, company_id)',
            'Le code de la catégorie doit être unique par société.',
        ),
    ]

    @api.depends('request_ids')
    def _compute_request_count(self):
        for category in self:
            category.request_count = len(category.request_ids)

    def _compute_to_review_count(self):
        Request = self.env['approval.request']
        for category in self:
            category.to_review_count = Request.search_count([
                ('category_id', '=', category.id),
                ('can_current_user_approve', '=', True),
            ])

    def action_new_request(self):
        """Ouvre un formulaire de création pré-rempli pour une nouvelle
        demande dans cette catégorie, utilisé par le bouton
        'Nouvelle demande' de la carte du tableau de bord."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle demande - %s') % self.name,
            'res_model': 'approval.request',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                'default_category_id': self.id,
                'default_workflow_id': self.workflow_id.id,
            },
        }

    def action_view_to_review(self):
        """Ouvre la liste des demandes de cette catégorie en attente
        d'approbation par l'utilisateur actuel, utilisé par le bouton
        'À examiner' de la carte du tableau de bord."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('À examiner - %s') % self.name,
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('category_id', '=', self.id),
                ('can_current_user_approve', '=', True),
            ],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].strip().upper()
        return super().write(vals)

    @api.constrains('code')
    def _check_code(self):
        for category in self:
            if not category.code:
                raise ValidationError(
                    'Le code de la catégorie est obligatoire.'
                )

            if category.code != category.code.strip().upper():
                raise ValidationError(
                    'Le code de la catégorie doit être en majuscules '
                    'et ne doit pas contenir d espaces au début ou à la fin.'
                )
