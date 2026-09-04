# -*- coding: utf-8 -*-

from odoo import fields, models


class ApprovalHistory(models.Model):
    _name = 'approval.history'
    _description = 'Historique des approbations'
    _order = 'create_date desc'

    request_id = fields.Many2one(
        'approval.request',
        string='Demande',
        required=True,
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur',
        required=True,
        default=lambda self: self.env.user,
    )

    action = fields.Selection(
        [
            ('created', 'Créée'),
            ('submitted', 'Soumise'),
            ('approved', 'Approuvée'),
            ('refused', 'Refusée'),
            ('cancelled', 'Annulée'),
            ('stage_changed', 'Étape modifiée'),
        ],
        string='Action',
        required=True,
    )

    description = fields.Text(
        string='Description',
    )

    action_date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True,
    )
