# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    """Intégration du moteur AWE sur les bons de commande fournisseur.

    Comme pour sale.order, ce module n'implémente aucune logique de
    workflow ici : il se contente de fournir à AWE
    (`approval.request.create_for_document`) les informations
    pertinentes de la RFQ / commande d'achat. purchase.order reste
    propriétaire de son cycle de vie natif (`state`).
    """

    _inherit = 'purchase.order'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à cette commande '
             'd\'achat, si une validation a été demandée.',
    )

    approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation",
        readonly=True,
        store=False,
    )

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur la RFQ / commande d'achat.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents de la commande.
        """
        self.ensure_one()

        if self.state not in ('draft', 'sent'):
            raise UserError(
                "Seules les demandes de prix (état brouillon ou "
                "envoyée) peuvent être soumises pour approbation."
            )

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour "
                "cette commande d'achat : %s." % self.approval_request_id.name
            )

        request = self.env['approval.request'].create_for_document(
            self,
            'PURCHASE_REQUEST',
            extra_vals={
                'vendor_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount': self.amount_total,
                'amount_untaxed': self.amount_untaxed,
                'tax_amount': self.amount_tax,
                'order_date': self.date_order and self.date_order.date(),
                'description': (
                    'Validation de la commande d\'achat %s pour %s.'
                    % (self.name, self.partner_id.name)
                ),
                'justification': self.origin or '',
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à cette
        commande d'achat."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "cette commande d'achat.")

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
    # / refusal_action_method (configurés sur cat_purchase).
    # ============================================================

    def action_awe_approve(self):
        """Confirme la RFQ avec la méthode native une fois
        l'approbation finale atteinte. button_confirm() gère déjà
        nativement la double validation d'achat (state 'to approve'
        si applicable)."""
        for order in self:
            if order.state in ('draft', 'sent'):
                order.button_confirm()
        return True

    def action_awe_refuse(self):
        """Annule la RFQ / commande d'achat avec la méthode native
        lorsque la demande d'approbation est refusée."""
        for order in self:
            if order.state != 'cancel':
                order.button_cancel()
        return True