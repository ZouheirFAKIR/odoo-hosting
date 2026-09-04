# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalRule(models.Model):
    """Règle métier conditionnelle déterminant quel workflow appliquer
    à une demande, en fonction de critères tels que le montant, le
    département, la société ou le poste de l'employé.

    Exemple : "Si catégorie = Achat ET montant >= 1000 MAD, alors
    appliquer le workflow 'Manager + Directeur'".

    Les règles d'une même catégorie sont évaluées par ordre de
    séquence ; la première règle dont les conditions sont satisfaites
    l'emporte. Si aucune règle ne correspond, le workflow par défaut
    de la catégorie (approval.category.workflow_id) est utilisé.
    """
    _name = 'approval.rule'
    _description = "Règle de sélection de workflow"
    _order = 'category_id, sequence'

    name = fields.Char(string="Nom de la règle", required=True, translate=True)
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True,
    )

    category_id = fields.Many2one(
        'approval.category',
        string="Catégorie",
        required=True,
        ondelete='cascade',
        help="Catégorie de demande à laquelle s'applique cette règle.",
    )

    workflow_id = fields.Many2one(
        'approval.workflow',
        string="Workflow à appliquer",
        required=True,
        help="Workflow déclenché si les conditions de cette règle sont "
             "satisfaites.",
    )

    # --- Conditions ---------------------------------------------------
    # Chaque condition est optionnelle : si le champ n'est pas rempli,
    # cette condition n'est simplement pas évaluée (elle est toujours
    # considérée comme vraie).

    amount_operator = fields.Selection(
        selection=[
            ('none', 'Aucune condition de montant'),
            ('<', 'Inférieur à'),
            ('<=', 'Inférieur ou égal à'),
            ('>', 'Supérieur à'),
            ('>=', 'Supérieur ou égal à'),
            ('=', 'Égal à'),
            ('between', 'Compris entre'),
        ],
        string="Condition sur la mesure",
        default='none',
    )
    condition_field = fields.Selection(
        selection=[
            ('amount', 'Montant / Coût'),
            ('duration', 'Durée (jours)'),
            ('quantity', 'Quantité'),
            ('discount', 'Remise (%)'),
        ],
        string="Mesure évaluée",
        default='amount',
        required=True,
        help="Quelle valeur de la demande est comparée par la condition "
             "ci-dessus. Exemple : 'Montant' pour une demande d'achat, "
             "'Durée' pour un congé, 'Quantité' pour un transfert de "
             "stock, 'Remise' pour une commande client.",
    )
    amount_value = fields.Monetary(
        string="Valeur de référence", currency_field='currency_id',
    )
    amount_value_to = fields.Monetary(
        string="Valeur de référence (borne haute)",
        currency_field='currency_id',
        help="Utilisé uniquement si l'opérateur est 'Compris entre'.",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
    )

    training_type_value = fields.Selection(
        selection=[
            ('internal', 'Interne'),
            ('external', 'Externe'),
            ('online', 'En ligne'),
        ],
        string="Type de formation",
        help="Si renseigné, la règle ne s'applique qu'aux demandes de "
             "formation de ce type (catégorie 'Demande de formation' "
             "uniquement).",
    )

    department_id = fields.Many2one(
        'hr.department',
        string="Département",
        help="Si renseigné, la règle ne s'applique qu'aux demandes des "
             "employés de ce département.",
    )
    job_id = fields.Many2one(
        'hr.job',
        string="Poste",
        help="Si renseigné, la règle ne s'applique qu'aux demandes des "
             "employés occupant ce poste.",
    )

    stock_location_id = fields.Many2one(
        'stock.location',
        string="Emplacement sensible",
        help="Si renseigné, la règle ne s'applique qu'aux demandes de "
             "transfert de stock dont l'emplacement de destination "
             "est celui-ci (catégorie 'Transfert de stock' "
             "uniquement).",
    )

    workflow_id_help = fields.Char(
        compute='_compute_workflow_id_help', string="Résumé",
    )

    @api.depends('name', 'category_id', 'workflow_id')
    def _compute_workflow_id_help(self):
        for rule in self:
            rule.workflow_id_help = (
                f"{rule.category_id.name or '?'} → {rule.workflow_id.name or '?'}"
            )

    @api.constrains('amount_operator', 'amount_value', 'amount_value_to')
    def _check_amount_condition(self):
        for rule in self:
            if rule.amount_operator == 'between' and rule.amount_value_to <= rule.amount_value:
                raise ValidationError(
                    "Pour une condition 'Compris entre', le montant "
                    "haut doit être strictement supérieur au montant bas."
                )

    def _matches(self, values=None, department=None, job=None,
                 training_type=None, location=None):
        """Vérifie si les conditions de CETTE règle sont satisfaites
        pour les critères fournis.

        :param values: dict des mesures de la demande, ex.
            {'amount': 8500.0, 'duration': 5, 'quantity': 20,
             'discount': 12.0}. La mesure réellement comparée dépend
            du champ `condition_field` de la règle.
        :param department: enregistrement hr.department ou None
        :param job: enregistrement hr.job ou None
        :param training_type: 'internal'/'external'/'online' ou None
        :param location: enregistrement stock.location (destination)
            ou None
        :return: bool
        """
        self.ensure_one()
        values = values or {}
        measure = values.get(self.condition_field, 0.0) or 0.0

        # Condition sur la mesure (montant, durée, quantité, remise...)
        if self.amount_operator != 'none':
            if self.amount_operator == '<' and not (measure < self.amount_value):
                return False
            if self.amount_operator == '<=' and not (measure <= self.amount_value):
                return False
            if self.amount_operator == '>' and not (measure > self.amount_value):
                return False
            if self.amount_operator == '>=' and not (measure >= self.amount_value):
                return False
            if self.amount_operator == '=' and not (measure == self.amount_value):
                return False
            if self.amount_operator == 'between' and not (
                self.amount_value <= measure <= self.amount_value_to
            ):
                return False

        # Condition de département
        if self.department_id and (not department or department.id != self.department_id.id):
            return False

        # Condition de poste
        if self.job_id and (not job or job.id != self.job_id.id):
            return False

        # Condition de type de formation
        if self.training_type_value and self.training_type_value != training_type:
            return False

        # Condition d'emplacement sensible (transfert de stock)
        if self.stock_location_id and (not location or location.id != self.stock_location_id.id):
            return False

        return True

    @api.model
    def find_workflow(self, category, amount=0.0, department=None, job=None,
                       duration=0.0, quantity=0.0, discount=0.0,
                       training_type=None, location=None):
        """Point d'entrée principal : détermine quel workflow appliquer
        pour une catégorie et des critères donnés, en évaluant les
        règles actives de cette catégorie par ordre de séquence.

        Retombe sur le workflow par défaut de la catégorie si aucune
        règle ne correspond.

        :param category: enregistrement approval.category
        :param amount: montant de la demande
        :param department: enregistrement hr.department ou None
        :param job: enregistrement hr.job ou None
        :param duration: durée en jours (congé, formation)
        :param quantity: quantité (transfert de stock)
        :param discount: remise en % (commande client)
        :param training_type: type de formation ou None
        :param location: emplacement de destination (transfert de
            stock) ou None
        :return: enregistrement approval.workflow (peut être vide)
        """
        rules = self.search([
            ('category_id', '=', category.id),
            ('active', '=', True),
        ], order='sequence')

        values = {
            'amount': amount,
            'duration': duration,
            'quantity': quantity,
            'discount': discount,
        }

        for rule in rules:
            if rule._matches(values=values, department=department, job=job,
                              training_type=training_type, location=location):
                return rule.workflow_id

        return category.workflow_id