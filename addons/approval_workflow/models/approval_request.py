# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Demande d\'approbation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'

    # ============================================================
    # INFORMATIONS DE BASE
    # ============================================================

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        default='New',
        tracking=True,
    )

    requester_id = fields.Many2one(
        'res.users',
        string='Demandeur',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        tracking=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )

    category_id = fields.Many2one(
        'approval.category',
        string='Catégorie',
        required=True,
        tracking=True,
    )

    category_use_product_lines = fields.Boolean(
        string='La catégorie nécessite des produits',
        related='category_id.use_product_lines',
        readonly=True,
    )

    category_type = fields.Selection(
        related='category_id.category_type',
        string='Type de catégorie',
        store=True,
        readonly=True,
    )

    # ============================================================
    # DOCUMENT MÉTIER LIÉ
    # ============================================================

    res_model = fields.Char(
        string='Modèle du document lié',
        readonly=True,
        copy=False,
        index=True,
    )

    res_id = fields.Integer(
        string='ID du document lié',
        readonly=True,
        copy=False,
    )

    related_document_name = fields.Char(
        string='Document lié',
        compute='_compute_related_document_name',
    )

    # ============================================================
    # LIGNES DE PRODUITS
    # ============================================================

    line_ids = fields.One2many(
        'approval.request.line',
        'request_id',
        string='Lignes de produits',
    )

    # ============================================================
    # WORKFLOW
    # ============================================================

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        tracking=True,
    )

    current_stage_id = fields.Many2one(
        'approval.stage',
        string='Étape en cours',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approval_line_ids = fields.One2many(
        'approval.line',
        'request_id',
        string='Lignes d\'approbation',
    )

    history_ids = fields.One2many(
        'approval.history',
        'request_id',
        string='Historique',
    )

    approval_count = fields.Integer(
        string='Lignes d\'approbation',
        compute='_compute_approval_count',
    )

    history_count = fields.Integer(
        string='Historique',
        compute='_compute_history_count',
    )

    # ============================================================
    # DATES / STATUT
    # ============================================================

    date_request = fields.Datetime(
        string='Date de la demande',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )

    date_submitted = fields.Datetime(
        string='Date de soumission',
        readonly=True,
        copy=False,
    )

    date_end = fields.Datetime(
        string='Date de clôture',
        readonly=True,
        copy=False,
        help='Date à laquelle la demande a atteint un état final.',
    )

    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('in_progress', 'En cours'),
            ('approved', 'Approuvée'),
            ('refused', 'Refusée'),
            ('cancelled', 'Annulée'),
        ],
        string='Statut',
        default='draft',
        required=True,
        tracking=True,
    )

    priority = fields.Selection(
        [
            ('0', 'Normale'),
            ('1', 'Haute'),
            ('2', 'Urgente'),
        ],
        string='Priorité',
        default='0',
        tracking=True,
    )

    can_current_user_approve = fields.Boolean(
        string='L\'utilisateur actuel peut approuver',
        compute='_compute_can_current_user_approve',
        search='_search_can_current_user_approve',
    )

    # ============================================================
    # INFORMATIONS FINANCIÈRES
    # ============================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )

    amount = fields.Monetary(
        string='Montant',
        default=0.0,
        currency_field='currency_id',
        tracking=True,
    )

    amount_untaxed = fields.Monetary(
        string='Montant hors taxes',
        currency_field='currency_id',
    )

    tax_amount = fields.Monetary(
        string='Taxes',
        currency_field='currency_id',
    )

    discount = fields.Float(
        string='Remise (%)',
    )

    # ============================================================
    # INFORMATIONS GÉNÉRALES
    # ============================================================

    description = fields.Text(
        string='Description',
    )

    comment = fields.Text(
        string='Commentaire',
        help='Remarque libre.',
    )

    justification = fields.Text(
        string='Justification',
        help="Utilisé par les demandes d'achat, de note de frais et de formation.",
    )

    reason = fields.Text(
        string='Motif',
        help='Utilisé par les demandes de congé et de transfert de stock.',
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Fournisseur / Prestataire',
    )

    date_from = fields.Date(
        string='Du',
    )

    date_to = fields.Date(
        string='Au',
    )

    duration = fields.Float(
        string='Durée (jours)',
        compute='_compute_duration',
        store=True,
    )

    location = fields.Char(
        string='Lieu',
    )

    # ============================================================
    # DEMANDE D'ACHAT
    # ============================================================

    requested_date = fields.Date(
        string='Date de livraison demandée',
    )

    # ============================================================
    # VALIDATION DE COMMANDE DE VENTE
    # ============================================================

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Vendeur',
    )

    order_date = fields.Date(
        string='Date de commande',
    )

    requested_delivery_date = fields.Date(
        string='Date de livraison demandée (Vente)',
    )

    # ============================================================
    # DEMANDE DE CONGÉ
    # ============================================================

    holiday_type_id = fields.Many2one(
        'hr.leave.type',
        string='Type de congé',
    )

    leave_id = fields.Many2one(
        'hr.leave',
        string='Congé lié',
        readonly=True,
        copy=False,
    )

    # ============================================================
    # VALIDATION DE NOTE DE FRAIS
    # ============================================================

    expense_type = fields.Selection(
        [
            ('transport', 'Transport'),
            ('accommodation', 'Hébergement'),
            ('meal', 'Repas'),
            ('supplies', 'Fournitures'),
            ('other', 'Autre'),
        ],
        string='Type de dépense',
    )

    expense_date = fields.Date(
        string='Date de la dépense',
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Espèces'),
            ('bank_transfer', 'Virement bancaire'),
            ('company_card', 'Carte entreprise'),
            ('other', 'Autre'),
        ],
        string='Mode de paiement',
    )

    receipt = fields.Binary(
        string='Justificatif',
        attachment=True,
    )

    receipt_filename = fields.Char(
        string='Nom du fichier justificatif',
    )

    expense_id = fields.Many2one(
        'hr.expense',
        string='Note de frais liée',
        readonly=True,
        copy=False,
    )

    # ============================================================
    # DEMANDE DE FORMATION
    # ============================================================

    training_name = fields.Char(
        string='Nom de la formation',
    )

    training_type = fields.Selection(
        [
            ('internal', 'Interne'),
            ('external', 'Externe'),
            ('online', 'En ligne'),
        ],
        string='Type de formation',
    )

    objective = fields.Text(
        string='Objectif',
    )

    # ============================================================
    # TRANSFERT DE STOCK
    # ============================================================

    source_location_id = fields.Many2one(
        'stock.location',
        string='Emplacement source',
    )

    destination_location_id = fields.Many2one(
        'stock.location',
        string='Emplacement de destination',
    )

    scheduled_date = fields.Date(
        string='Date planifiée',
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Transfert lié',
        readonly=True,
        copy=False,
    )

    # ============================================================
    # CHAMPS CALCULÉS
    # ============================================================

    @api.depends('history_ids')
    def _compute_history_count(self):
        for request in self:
            request.history_count = len(request.history_ids)

    @api.depends('approval_line_ids')
    def _compute_approval_count(self):
        for request in self:
            request.approval_count = len(request.approval_line_ids)

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        for request in self:
            if request.date_from and request.date_to:
                delta = (
                    request.date_to - request.date_from
                ).days + 1
                request.duration = max(delta, 0)
            else:
                request.duration = 0.0

    @api.depends('res_model', 'res_id')
    def _compute_related_document_name(self):
        for request in self:
            record = request._get_related_record()
            request.related_document_name = (
                record.display_name if record else False
            )

    @api.depends(
        'state',
        'current_stage_id',
        'approval_line_ids.state',
        'approval_line_ids.approver_id',
    )
    def _compute_can_current_user_approve(self):
        for request in self:
            request.can_current_user_approve = (
                request._user_can_approve()
            )

    # ============================================================
    # OUTILS POUR LE DOCUMENT LIÉ
    # ============================================================

    def _get_related_record(self):
        self.ensure_one()

        if not self.res_model or not self.res_id:
            return self.env['approval.request']

        if self.res_model not in self.env:
            return self.env['approval.request']

        return self.env[self.res_model].browse(
            self.res_id
        ).exists()

    def action_view_related_document(self):
        self.ensure_one()

        record = self._get_related_record()

        if not record:
            raise UserError(
                _('Aucun document métier lié n\'a été trouvé.')
            )

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ============================================================
    # DROIT D'APPROBATION
    # ============================================================

    def _user_can_approve(self):
        self.ensure_one()

        if self.state != 'in_progress':
            return False

        if not self.current_stage_id:
            return False

        approvers = (
            self.current_stage_id.get_possible_approvers(self)
        )

        if self.env.user not in approvers:
            return False

        already_voted = self.approval_line_ids.filtered(
            lambda line:
            line.stage_id == self.current_stage_id
            and line.approver_id == self.env.user
            and line.state != 'pending'
        )

        return not already_voted

    def _search_can_current_user_approve(
        self,
        operator,
        value,
    ):
        requests = self.search([])

        matching_ids = requests.filtered(
            lambda request: request._user_can_approve()
        ).ids

        if operator == '=' and value:
            return [('id', 'in', matching_ids)]

        if operator == '=' and not value:
            return [('id', 'not in', matching_ids)]

        if operator == '!=' and value:
            return [('id', 'not in', matching_ids)]

        if operator == '!=' and not value:
            return [('id', 'in', matching_ids)]

        return [('id', 'in', [])]

    # ============================================================
    # CONTRAINTES
    # ============================================================

    @api.constrains('amount')
    def _check_amount_positive(self):
        for request in self:
            if request.amount < 0:
                raise ValidationError(
                    _('Le montant de la demande ne peut pas être négatif.')
                )

    @api.constrains(
        'res_model',
        'res_id',
        'state',
    )
    def _check_no_duplicate_active_request(self):
        for request in self:

            if not request.res_model or not request.res_id:
                continue

            if request.state in (
                'approved',
                'refused',
                'cancelled',
            ):
                continue

            other = self.search(
                [
                    ('id', '!=', request.id),
                    ('res_model', '=', request.res_model),
                    ('res_id', '=', request.res_id),
                    (
                        'state',
                        'not in',
                        (
                            'approved',
                            'refused',
                            'cancelled',
                        ),
                    ),
                ],
                limit=1,
            )

            if other:
                raise ValidationError(
                    _(
                        'Une demande d\'approbation active existe déjà '
                        'pour ce document (%s).'
                    ) % other.name
                )

    # ============================================================
    # NOTIFICATIONS (EMAIL + CHATTER/ACTIVITÉ)
    # ============================================================

    def _notify_send_mail(self, template_xmlid, partner, extra_email_values=None):
        """Envoie un mail.template à un seul partenaire dynamique (jamais
        une adresse codée en dur). Utilise les surcharges email_to +
        recipient_ids pour que le destinataire soit toujours résolu au
        moment de l'envoi, évitant ainsi les doublons et les erreurs
        de destinataire.
        """
        self.ensure_one()

        if not partner:
            return

        template = self.env.ref(
            'approval_workflow.%s' % template_xmlid,
            raise_if_not_found=False,
        )

        if not template:
            return

        email_values = {
            'email_to': False,
            'recipient_ids': [(6, 0, partner.ids)],
        }

        if extra_email_values:
            email_values.update(extra_email_values)

        template.send_mail(
            self.id,
            force_send=True,
            email_values=email_values,
        )

    def _notify_approvers(self, approvers):
        """Notifie (email + activité) chaque approbateur de l'étape en
        cours qu'une demande est en attente de leur décision. Appelée
        à la soumission et à chaque passage à une nouvelle étape.
        """
        self.ensure_one()

        for approver in approvers:

            partner = approver.partner_id

            self._notify_send_mail(
                'mail_template_approval_pending',
                partner,
            )

            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Demande d\'approbation à examiner : %s') % self.name,
                note=_(
                    'La demande %(name)s est en attente de votre '
                    'approbation (étape : %(stage)s).'
                ) % {
                    'name': self.name,
                    'stage': self.current_stage_id.name
                    if self.current_stage_id else '',
                },
                user_id=approver.id,
            )

        if approvers:
            self.message_post(
                body=_(
                    'Notification envoyée au(x) approbateur(s) : %s.'
                ) % ', '.join(approvers.mapped('name')),
            )

    def _notify_requester(self, template_xmlid, body):
        """Notifie (email + chatter) le demandeur de la demande (l'utilisateur
        qui l'a soumise), jamais l'utilisateur actuellement connecté.
        """
        self.ensure_one()

        requester = self.requester_id

        if not requester:
            return

        self._notify_send_mail(
            template_xmlid,
            requester.partner_id,
        )

        self.message_post(
            body=body,
            partner_ids=requester.partner_id.ids,
        )

        # Clôture les activités "à examiner" encore en attente sur cette
        # demande (par exemple laissées par les approbateurs), car la
        # demande vient de quitter l'étape d'approbation.
        self.activity_ids.filtered(
            lambda act: act.user_id != requester
        ).action_feedback(feedback=_('Demande traitée.'))

    # ============================================================
    # HISTORIQUE
    # ============================================================

    def _create_history(self, action, description):
        self.ensure_one()

        self.env['approval.history'].create({
            'request_id': self.id,
            'user_id': self.env.user.id,
            'action': action,
            'description': description,
        })

    def action_view_history(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Historique des approbations'),
            'res_model': 'approval.history',
            'view_mode': 'list,form',
            'domain': [
                ('request_id', '=', self.id),
            ],
        }

    # ============================================================
    # LIGNES D'APPROBATION
    # ============================================================

    def _create_stage_lines(self, stage):
        self.ensure_one()

        approvers = stage.get_possible_approvers(self)

        for approver in approvers:

            existing = self.approval_line_ids.filtered(
                lambda line:
                line.stage_id == stage
                and line.approver_id == approver
            )

            if not existing:
                self.env['approval.line'].create({
                    'request_id': self.id,
                    'stage_id': stage.id,
                    'approver_id': approver.id,
                    'state': 'pending',
                    'is_required': True,
                })

    def action_view_approvals(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lignes d\'approbation'),
            'res_model': 'approval.line',
            'view_mode': 'list,form',
            'domain': [
                ('request_id', '=', self.id),
            ],
        }

    # ============================================================
    # ACTION FINALE
    # ============================================================

    def _run_final_action(self):
        for request in self:

            method_name = (
                request.category_id.final_action_method
            )

            if not method_name:
                continue

            record = request._get_related_record()

            if not record:
                continue

            if not hasattr(record, method_name):
                continue

            getattr(record, method_name)()

    # ============================================================
    # ACTION DE REFUS
    # ============================================================

    def _run_refusal_action(self):
        for request in self:

            method_name = (
                request.category_id.refusal_action_method
            )

            if not method_name:
                continue

            record = request._get_related_record()

            if not record:
                continue

            if not hasattr(record, method_name):
                continue

            getattr(record, method_name)()

    # ============================================================
    # CRÉATION
    # ============================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'approval.request'
                    )
                    or 'New'
                )

            if not vals.get('requester_id'):
                vals['requester_id'] = self.env.user.id

            if not vals.get('employee_id'):
                employee = self.env['hr.employee'].search(
                    [
                        (
                            'user_id',
                            '=',
                            vals.get('requester_id'),
                        )
                    ],
                    limit=1,
                )

                if employee:
                    vals['employee_id'] = employee.id

        requests = super().create(vals_list)

        for request in requests:
            request._create_history(
                'created',
                'Demande d\'approbation créée.',
            )

        return requests

    # ============================================================
    # ONCHANGE
    # ============================================================

    @api.onchange('category_id')
    def _onchange_category_id(self):

        if self.category_id:
            self.workflow_id = self.category_id.workflow_id

    @api.onchange('line_ids')
    def _onchange_line_ids(self):

        if (
            self.category_id
            and self.category_id.use_product_lines
        ):
            self.amount = sum(
                self.line_ids.mapped('subtotal')
            )

    # ============================================================
    # CRÉER UNE DEMANDE POUR UN DOCUMENT MÉTIER EXTERNE
    # ============================================================

    @api.model
    def create_for_document(
        self,
        record,
        category_code,
        extra_vals=None,
    ):
        category = self.env[
            'approval.category'
        ].search(
            [
                ('code', '=', category_code),
            ],
            limit=1,
        )

        if not category:
            raise UserError(
                _(
                    "Aucune catégorie d'approbation configurée avec le "
                    "code '%s'. Veuillez la créer dans Approbations > "
                    "Configuration > Catégories."
                ) % category_code
            )

        existing = self.search(
            [
                ('res_model', '=', record._name),
                ('res_id', '=', record.id),
                (
                    'state',
                    'not in',
                    (
                        'approved',
                        'refused',
                        'cancelled',
                    ),
                ),
            ],
            limit=1,
        )

        if existing:
            raise UserError(
                _(
                    'Une demande d\'approbation est déjà en cours '
                    'pour ce document : %s.'
                ) % existing.name
            )

        vals = {
            'category_id': category.id,
            'res_model': record._name,
            'res_id': record.id,
        }

        vals.update(extra_vals or {})

        request = self.create(vals)

        request.action_submit()

        return request

    # ============================================================
    # SOUMETTRE
    # ============================================================

    def action_submit(self):

        for request in self:

            if request.state != 'draft':
                raise UserError(
                    _(
                        'Seules les demandes en brouillon '
                        'peuvent être soumises.'
                    )
                )

            workflow = request.workflow_id

            if not workflow:

                quantity = sum(
                    request.line_ids.mapped('quantity')
                )

                department = (
                    request.employee_id.department_id
                    if request.employee_id
                    else False
                )

                job = (
                    request.employee_id.job_id
                    if request.employee_id
                    else False
                )

                rule_workflow = (
                    self.env['approval.rule'].find_workflow(
                        request.category_id,
                        amount=request.amount,
                        department=department,
                        job=job,
                        duration=request.duration,
                        quantity=quantity,
                        discount=request.discount,
                        training_type=request.training_type,
                        location=request.destination_location_id,
                    )
                )

                workflow = (
                    rule_workflow
                    or request.category_id.workflow_id
                )

            if not workflow:
                raise UserError(
                    _(
                        'Aucun workflow d\'approbation n\'est '
                        'configuré pour cette demande.'
                    )
                )

            stages = workflow.stage_ids.filtered('active')

            if not stages:
                raise UserError(
                    _(
                        'Le workflow sélectionné ne comporte aucune '
                        'étape d\'approbation active.'
                    )
                )

            request.workflow_id = workflow

            first_stage = workflow.get_first_stage()

            if not first_stage:
                raise UserError(
                    _(
                        'Aucune première étape d\'approbation n\'a pu '
                        'être trouvée.'
                    )
                )

            request.current_stage_id = first_stage
            request.state = 'in_progress'
            request.date_submitted = fields.Datetime.now()

            request._create_stage_lines(first_stage)

            request._create_history(
                'submitted',
                'Demande d\'approbation soumise.',
            )

            approvers = first_stage.get_possible_approvers(request)
            request._notify_approvers(approvers)

        return True

    # ============================================================
    # APPROUVER
    # ============================================================

    def action_approve(self):

        for request in self:

            if request.state != 'in_progress':
                raise UserError(
                    _(
                        'Seules les demandes en cours peuvent être '
                        'approuvées.'
                    )
                )

            if not request.current_stage_id:
                raise UserError(
                    _(
                        'Aucune étape d\'approbation en cours n\'est '
                        'définie.'
                    )
                )

            stage = request.current_stage_id

            approvers = stage.get_possible_approvers(request)

            if self.env.user not in approvers:
                raise UserError(
                    _(
                        'Vous n\'êtes pas autorisé à approuver '
                        'cette demande.'
                    )
                )

            line = request.approval_line_ids.filtered(
                lambda line:
                line.stage_id == stage
                and line.approver_id == self.env.user
                and line.state == 'pending'
            )[:1]

            if not line:
                raise UserError(
                    _(
                        'Vous avez déjà traité cette étape '
                        'd\'approbation.'
                    )
                )

            line.write({
                'state': 'approved',
                'action_date': fields.Datetime.now(),
            })

            request._create_history(
                'approved',
                'Demande approuvée par %s.'
                % self.env.user.name,
            )

            # Marque uniquement l'activité de cet approbateur comme
            # terminée, sans toucher aux autres approbateurs encore
            # en attente.
            request.activity_ids.filtered(
                lambda act: act.user_id == self.env.user
            ).action_feedback(
                feedback=_('Approuvée par %s.') % self.env.user.name
            )

            approved_count = len(
                request.approval_line_ids.filtered(
                    lambda approval_line:
                    approval_line.stage_id == stage
                    and approval_line.state == 'approved'
                )
            )

            if approved_count >= stage.min_approvals:

                next_stage = (
                    request.workflow_id.get_next_stage(stage)
                )

                if next_stage:

                    request.current_stage_id = next_stage

                    request._create_stage_lines(next_stage)

                    request._create_history(
                        'stage_changed',
                        'Approbation passée à l\'étape : %s.'
                        % next_stage.name,
                    )

                    next_approvers = (
                        next_stage.get_possible_approvers(request)
                    )
                    request._notify_approvers(next_approvers)

                else:

                    request.current_stage_id = False
                    request.state = 'approved'
                    request.date_end = fields.Datetime.now()

                    request._create_history(
                        'approved',
                        'Toutes les étapes d\'approbation ont été '
                        'complétées.',
                    )

                    request._notify_requester(
                        'mail_template_approval_approved',
                        _(
                            'Demande approuvée. Toutes les étapes '
                            'd\'approbation ont été complétées.'
                        ),
                    )

                    request._run_final_action()

        return True

    # ============================================================
    # REFUSER
    # ============================================================

    def action_refuse(self):

        for request in self:

            if request.state != 'in_progress':
                raise UserError(
                    _(
                        'Seules les demandes en cours peuvent être '
                        'refusées.'
                    )
                )

            if (
                request.current_stage_id
                and request.current_stage_id.is_blocking
            ):

                lines = request.approval_line_ids.filtered(
                    lambda line:
                    line.stage_id == request.current_stage_id
                    and line.approver_id == self.env.user
                    and line.state == 'pending'
                )

                if not lines:
                    raise UserError(
                        _(
                            'Vous n\'êtes pas autorisé à refuser '
                            'cette demande.'
                        )
                    )

                lines.write({
                    'state': 'refused',
                    'action_date': fields.Datetime.now(),
                })

                request.state = 'refused'
                request.date_end = fields.Datetime.now()

                request._create_history(
                    'refused',
                    'Demande refusée par %s.'
                    % self.env.user.name,
                )

                refusal_body = _(
                    'Demande refusée par %s.'
                ) % self.env.user.name

                if request.reason:
                    refusal_body += _(
                        '<br/>Motif : %s'
                    ) % request.reason

                request._notify_requester(
                    'mail_template_approval_refused',
                    refusal_body,
                )

                request._run_refusal_action()

        return True

    # ============================================================
    # ANNULER
    # ============================================================

    def action_cancel(self):

        for request in self:

            if request.state in (
                'approved',
                'refused',
                'cancelled',
            ):
                raise UserError(
                    _(
                        'Cette demande ne peut plus être annulée.'
                    )
                )

            request.state = 'cancelled'
            request.current_stage_id = False
            request.date_end = fields.Datetime.now()

            request._create_history(
                'cancelled',
                'Demande annulée par %s.'
                % self.env.user.name,
            )

        return True

    # ============================================================
    # REMETTRE EN BROUILLON
    # ============================================================

    def action_reset_to_draft(self):

        for request in self:

            if request.state not in (
                'cancelled',
                'refused',
            ):
                raise UserError(
                    _(
                        'Seules les demandes annulées ou refusées '
                        'peuvent être remises en brouillon.'
                    )
                )

            request.write({
                'state': 'draft',
                'current_stage_id': False,
                'date_submitted': False,
                'date_end': False,
            })

            request.approval_line_ids.unlink()

            request._create_history(
                'created',
                'Demande remise en brouillon.',
            )

        return True
