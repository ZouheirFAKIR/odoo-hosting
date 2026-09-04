# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrLeave(models.Model):
    """Intégration du moteur AWE sur les demandes de congé.

    Comme pour les autres intégrations, ce module ne réimplémente
    aucune logique de workflow ici : il se contente de fournir à AWE
    (`approval.request.create_for_document`) les informations
    pertinentes du congé. Le moteur AWE reste seul responsable de la
    sélection du workflow (via `approval.rule.find_workflow`, sur la
    base de la durée calculée automatiquement à partir de date_from /
    date_to par `approval.request._compute_duration`). hr.leave reste
    propriétaire de son cycle de vie natif (`state`).
    """

    _inherit = 'hr.leave'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation AWE",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à ce congé, si une '
             'validation a été demandée.',
    )

    awe_approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation AWE",
        readonly=True,
        store=False,
    )

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur la demande de congé.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents du congé. La durée
        n'est pas transmise explicitement : elle est recalculée par
        AWE lui-même à partir de date_from / date_to, puis utilisée
        par `approval.rule.find_workflow(..., duration=...)` pour
        sélectionner le bon workflow.
        """
        self.ensure_one()

        if self.state != 'confirm':
            raise UserError(
                "Seules les demandes de congé en attente d'approbation "
                "(état « À approuver ») peuvent être soumises au "
                "moteur de workflow d'approbation. Veuillez d'abord "
                "confirmer la demande de congé."
            )

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour ce "
                "congé : %s." % self.approval_request_id.name
            )

        request = self.env['approval.request'].create_for_document(
            self,
            'LEAVE_REQUEST_2',
            extra_vals={
                'employee_id': self.employee_id.id,
                'holiday_type_id': self.holiday_status_id.id,
                'date_from': self.date_from and self.date_from.date(),
                'date_to': self.date_to and self.date_to.date(),
                'description': self.name or '',
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à ce
        congé."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "ce congé.")

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
    # / refusal_action_method (configurés sur cat_leave).
    # ============================================================

    def action_awe_approve(self):
        """Valide le congé avec le workflow natif hr.leave une fois
        l'approbation finale atteinte. 'confirm' -> action_approve()
        (gère nativement la double validation RH si configurée).
        'validate1' -> action_validate() pour le 2e palier natif si
        celui-ci n'a pas déjà été franchi."""
        for leave in self:
            if leave.state == 'confirm':
                leave.action_approve()
            elif leave.state == 'validate1':
                leave.action_validate()
        return True

    def action_awe_refuse(self):
        """Refuse le congé avec la méthode native lorsque la demande
        d'approbation AWE est refusée."""
        for leave in self:
            if leave.state in ('confirm', 'validate', 'validate1'):
                leave.action_refuse()
        return True