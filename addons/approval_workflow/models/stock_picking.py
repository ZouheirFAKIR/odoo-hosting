# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    """Intégration du moteur AWE sur les transferts de stock.

    Comme pour les autres intégrations, ce module ne réimplémente
    aucune logique de workflow ici : il se contente de fournir à AWE
    (`approval.request.create_for_document`) les informations
    pertinentes du transfert, notamment l'emplacement de destination,
    utilisé par `approval.rule.find_workflow(..., location=...)` pour
    détecter les emplacements sensibles. stock.picking reste
    propriétaire de son cycle de vie natif (`state`).
    """

    _inherit = 'stock.picking'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à ce transfert de '
             'stock, si une validation a été demandée.',
    )

    approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation",
        readonly=True,
        store=False,
    )

    def _prepare_approval_line_vals(self):
        """Construit les commandes One2many pour les lignes produit
        de la demande d'approbation, à partir des mouvements de stock
        du transfert. Permet à la quantité totale de remonter
        automatiquement jusqu'au moteur de règles AWE (le champ
        `quantity` utilisé par `approval.rule.find_workflow` est
        calculé par AWE lui-même comme la somme des lignes)."""
        self.ensure_one()

        line_commands = []

        for move in self.move_ids:
            if not move.product_id:
                continue

            line_commands.append((0, 0, {
                'product_id': move.product_id.id,
                'description': move.product_id.display_name,
                'product_uom_id': move.product_uom.id,
                'quantity': move.product_uom_qty,
                'price_unit': 0.0,
            }))

        return line_commands

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur le transfert de stock.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents du transfert.
        """
        self.ensure_one()

        if self.state in ('done', 'cancel'):
            raise UserError(
                "Ce transfert ne peut plus être soumis pour "
                "approbation (déjà effectué ou annulé)."
            )

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour "
                "ce transfert : %s." % self.approval_request_id.name
            )

        request = self.env['approval.request'].create_for_document(
            self,
            'STOCK_TRANSFER',
            extra_vals={
                'source_location_id': self.location_id.id,
                'destination_location_id': self.location_dest_id.id,
                'scheduled_date': (
                    self.scheduled_date and self.scheduled_date.date()
                ),
                'description': (
                    'Transfert de stock %s (%s -> %s).'
                    % (
                        self.name,
                        self.location_id.display_name,
                        self.location_dest_id.display_name,
                    )
                ),
                'reason': self.origin or '',
                'line_ids': self._prepare_approval_line_vals(),
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à ce
        transfert de stock."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "ce transfert.")

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
    # / refusal_action_method (configurés sur cat_stock).
    # ============================================================

    def action_awe_approve(self):
        """Fait passer le transfert au workflow normal Odoo
        (confirmé / prêt) une fois l'approbation finale atteinte.
        IMPORTANT : action_confirm() ne fait que confirmer les
        mouvements (draft -> confirmed/assigned) ; il n'appelle
        jamais action_assign() ni button_validate(). La validation
        physique reste une action séparée de l'utilisateur."""
        for picking in self:
            if picking.state not in ('done', 'cancel'):
                picking.action_confirm()
        return True

    def action_awe_refuse(self):
        """Annule le transfert avec la méthode native lorsque la
        demande d'approbation est refusée."""
        for picking in self:
            if picking.state not in ('done', 'cancel'):
                picking.action_cancel()
        return True