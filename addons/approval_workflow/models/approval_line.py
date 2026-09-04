# -*- coding: utf-8 -*-

from odoo import fields, models


class ApprovalLine(models.Model):
    _name = 'approval.line'
    _description = "Ligne d'approbation"
    _order = 'stage_id, id'

    request_id = fields.Many2one(
        'approval.request',
        string='Demande',
        required=True,
        ondelete='cascade',
    )

    stage_id = fields.Many2one(
        'approval.stage',
        string='Étape',
        required=True,
        ondelete='cascade',
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Approbateur',
        required=True,
    )

    state = fields.Selection(
        [
            ('pending', 'En attente'),
            ('approved', 'Approuvée'),
            ('refused', 'Refusée'),
        ],
        string='Statut',
        default='pending',
        required=True,
    )

    comment = fields.Text(
        string='Commentaire',
    )

    action_date = fields.Datetime(
        string="Date de l'action",
    )

    is_required = fields.Boolean(
        string='Requis',
        default=True,
    )
