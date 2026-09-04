# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    """Intégration du moteur AWE sur les commandes clients.

    IMPORTANT : ce module ne remplace ni ne duplique le cycle de vie
    natif de sale.order (`state`). Le statut d'approbation
    (`approval_state`) est un champ SÉPARÉ, purement informatif côté
    commande — c'est `approval.request` qui possède et gère son
    propre état (draft / in_progress / approved / refused /
    cancelled). sale.order reste propriétaire de son document et de
    son cycle de vente ; AWE ne fait qu'observer et, une fois
    l'approbation complète, appeler `action_confirm()` (configuré sur
    la catégorie via `final_action_method`, pas hardcodé ici).
    """

    _inherit = 'sale.order'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à cette commande, si '
             'une validation a été demandée.',
    )

    approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation",
        readonly=True,
        store=False,
    )

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur la commande client.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents de la commande.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(
                "Seuls les devis (état brouillon) peuvent être "
                "soumis pour approbation."
            )

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour "
                "cette commande : %s." % self.approval_request_id.name
            )

        discount = 0.0
        if self.order_line:
            discount = max(self.order_line.mapped('discount') or [0.0])

        request = self.env['approval.request'].create_for_document(
            self,
            'SALE_VALIDATION',
            extra_vals={
                'sale_order_id': self.id,
                'partner_id': self.partner_id.id,
                'salesperson_id': self.user_id.id,
                'order_date': self.date_order and self.date_order.date(),
                'amount_untaxed': self.amount_untaxed,
                'tax_amount': self.amount_tax,
                'amount': self.amount_total,
                'discount': discount,
                'description': (
                    'Validation de la commande %s pour %s.'
                    % (self.name, self.partner_id.name)
                ),
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à cette
        commande."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "cette commande.")

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
    # et _run_refusal_action() via approval.category.final_action_method
    # / refusal_action_method (configurés sur cat_sale). Le moteur AWE
    # ne connaît jamais sale.order directement : il appelle juste
    # getattr(record, method_name)(). Ces deux méthodes ne font
    # qu'orienter vers les méthodes 100% natives Odoo, après avoir
    # vérifié l'état courant (idempotence, pas de double exécution).
    # ============================================================

    def action_awe_approve(self):
        """Confirme le devis avec la méthode native une fois
        l'approbation finale atteinte. Ne fait rien si la commande
        n'est plus en brouillon (déjà confirmée ou annulée)."""
        for order in self:
            if order.state == 'draft':
                order.action_confirm()
        return True

    def action_awe_refuse(self):
        """Annule la commande avec la méthode native lorsque la
        demande d'approbation est refusée. `disable_cancel_warning`
        contourne le wizard de confirmation que action_cancel()
        renvoie normalement pour une commande non-brouillon (un
        wizard n'est pas exploitable dans un contexte automatique)."""
        for order in self:
            if order.state != 'cancel':
                order.with_context(
                    disable_cancel_warning=True
                ).action_cancel()
        return True