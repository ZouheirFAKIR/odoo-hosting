# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalStage(models.Model):
    _name = 'approval.stage'
    _description = "Étape d'approbation"
    _order = 'workflow_id, sequence, id'

    name = fields.Char(
        string="Nom de l'étape",
        required=True,
        translate=True,
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10,
        required=True,
    )

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade',
    )

    approver_type = fields.Selection(
        [
            ('user', 'Utilisateur spécifique'),
            ('group', "Groupe d'utilisateurs"),
            ('employee_manager', "Responsable de l'employé"),
        ],
        string="Type d'approbateur",
        default='user',
        required=True,
    )

    approver_user_id = fields.Many2one(
        'res.users',
        string='Approbateur',
    )

    approver_group_id = fields.Many2one(
        'res.groups',
        string="Groupe d'approbateurs",
    )

    min_approvals = fields.Integer(
        string="Nombre minimum d'approbations",
        default=1,
        required=True,
    )

    is_blocking = fields.Boolean(
        string='Étape bloquante',
        default=True,
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    approval_line_ids = fields.One2many(
        'approval.line',
        'stage_id',
        string="Lignes d'approbation",
    )

    @api.constrains(
        'approver_type',
        'approver_user_id',
        'approver_group_id',
    )
    def _check_approver(self):
        for stage in self:

            if stage.approver_type == 'user':
                if not stage.approver_user_id:
                    raise ValidationError(
                        'Un utilisateur spécifique doit être sélectionné.'
                    )

            elif stage.approver_type == 'group':
                if not stage.approver_group_id:
                    raise ValidationError(
                        "Un groupe d'approbateurs doit être sélectionné."
                    )

    @api.constrains('min_approvals')
    def _check_min_approvals(self):
        for stage in self:
            if stage.min_approvals < 1:
                raise ValidationError(
                    "Le nombre minimum d'approbations doit être au moins 1."
                )

    def get_possible_approvers(self, request):
        self.ensure_one()

        if self.approver_type == 'user':
            return self.approver_user_id

        if self.approver_type == 'group':
            return self.approver_group_id.users

        if self.approver_type == 'employee_manager':
            employee = request.employee_id

            if (
                employee
                and employee.parent_id
                and employee.parent_id.user_id
            ):
                return employee.parent_id.user_id

        return self.env['res.users']
