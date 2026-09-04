# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    """Intégration du moteur AWE sur les notes de dépense.

    Comme pour sale.order et purchase.order, ce module ne réimplémente
    aucune logique de workflow ici : il se contente de fournir à AWE
    (`approval.request.create_for_document`) les informations
    pertinentes de la dépense. hr.expense reste propriétaire de son
    cycle de vie natif (`state`).
    """

    _inherit = 'hr.expense'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à cette dépense, si '
             'une validation a été demandée.',
    )

    approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation",
        readonly=True,
        store=False,
    )

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur la note de dépense.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents de la dépense.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(
                "Seules les dépenses à l'état « À soumettre » "
                "(brouillon) peuvent être soumises pour approbation."
            )

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour "
                "cette dépense : %s." % self.approval_request_id.name
            )

        employee = self.employee_id

        request = self.env['approval.request'].create_for_document(
            self,
            'EXPENSE_VALIDATION',
            extra_vals={
                'employee_id': employee.id,
                'currency_id': self.currency_id.id,
                'amount': self.total_amount,
                'expense_date': self.date,
                'description': self.name,
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à cette
        dépense."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "cette dépense.")

        return {
            'type': 'ir.actions.act_window',
            'name': "Demande d'approbation",
            'res_model': 'approval.request',
            'res_id': self.approval_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ============================================================
    # AWE BUSINESS ACTION ADAPTERS
    #
    # Appelées dynamiquement par approval.request._run_final_action()
    # / _run_refusal_action() via approval.category.final_action_method
    # / refusal_action_method (configurés sur cat_expense).
    #
    # PARTICULARITÉ hr.expense : son champ `state` est calculé
    # (compute='_compute_state') à partir de `sheet_id.state` — il
    # n'existe donc AUCUNE méthode native sur hr.expense lui-même
    # capable de faire avancer son état. Le vrai workflow
    # d'approbation natif Odoo vit sur hr.expense.sheet
    # (_do_approve() / _do_refuse()). Ces adaptateurs créent la note
    # de frais si nécessaire (comme le bouton natif "Create Report"
    # le ferait) puis appellent les méthodes internes natives de
    # hr.expense.sheet — jamais un `state = ...` direct.
    # ============================================================

    def _awe_get_or_create_sheet(self):
        self.ensure_one()
        if not self.sheet_id:
            self._create_sheets_from_expense()
        return self.sheet_id

    def action_awe_approve(self):
        """Fait avancer la dépense dans le workflow standard Odoo
        (création de la note de frais si besoin, soumission puis
        approbation natives de cette note) une fois l'approbation
        finale AWE atteinte.

        BUG CORRIGÉ : hr.expense.sheet._do_approve() natif appelle en
        interne _check_can_create_move(), qui lève une UserError si
        la note de frais n'est pas déjà à l'état 'submit' ('Submitted').
        Une note fraîchement créée par _create_sheets_from_expense()
        reste à l'état 'draft' ('To Submit') tant qu'elle n'a pas été
        explicitement soumise. Appeler _do_approve() directement sur
        une note 'draft' faisait donc systématiquement échouer (et
        annuler) toute la transaction : c'est la cause du blocage
        observé sur Expense. On appelle donc d'abord la méthode
        native action_submit_sheet() ('draft' -> 'submit'), puis
        _do_approve() ('submit' -> 'approve'), en respectant l'ordre
        natif Odoo. Idempotent : ne rien refaire si déjà traité."""
        for expense in self:
            sheet = expense._awe_get_or_create_sheet()
            if not sheet:
                continue
            if sheet.state == 'draft':
                sheet.action_submit_sheet()
            if sheet.state == 'submit':
                sheet._do_approve()
        return True

    def action_awe_refuse(self):
        """Refuse la note de frais liée avec la méthode interne
        native lorsque la demande d'approbation AWE est refusée.

        BUG CORRIGÉ : un refus AWE intervient normalement AVANT toute
        approbation, donc AVANT que sheet_id n'ait jamais été créé (la
        note de frais n'était créée que dans action_awe_approve() ci-
        dessus). Avec `sheet = expense.sheet_id`, le sheet valait
        False dans ce cas -> la condition `if sheet and ...` était
        toujours fausse -> rien ne se passait, et `hr.expense.state`
        (calculé uniquement à partir de `sheet_id.state`) restait
        bloqué sur 'draft' indéfiniment : la dépense ne devenait
        jamais Refused/Cancelled. On utilise donc désormais
        `_awe_get_or_create_sheet()` (même helper que pour
        l'approbation) pour créer la note si besoin avant de la
        refuser nativement : `hr.expense.sheet` passe à l'état natif
        'cancel' (libellé "Refused" côté Odoo, l'équivalent natif de
        "Cancelled" pour ce modèle), et `hr.expense.state` se
        recalcule automatiquement en 'refused'."""
        for expense in self:
            sheet = expense._awe_get_or_create_sheet()
            if sheet and sheet.state != 'cancel':
                sheet._do_refuse(
                    _('Refusée via le moteur de workflow d\'approbation.')
                )
        return True