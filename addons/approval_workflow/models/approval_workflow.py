# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalWorkflow(models.Model):
    _name = 'approval.workflow'
    _description = "Workflow d'approbation"
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom du workflow',
        required=True,
        translate=True,
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    validation_type = fields.Selection(
        [
            ('sequential', 'Séquentiel'),
            ('parallel', 'Parallèle'),
        ],
        string='Type de validation',
        default='sequential',
        required=True,
    )

    stage_ids = fields.One2many(
        'approval.stage',
        'workflow_id',
        string="Étapes d'approbation",
    )

    category_ids = fields.One2many(
        'approval.category',
        'workflow_id',
        string='Catégories',
    )

    request_ids = fields.One2many(
        'approval.request',
        'workflow_id',
        string='Demandes',
    )

    stage_count = fields.Integer(
        string='Étapes',
        compute='_compute_stage_count',
    )

    request_count = fields.Integer(
        string='Demandes',
        compute='_compute_request_count',
    )

    @api.depends('stage_ids')
    def _compute_stage_count(self):
        for workflow in self:
            workflow.stage_count = len(workflow.stage_ids)

    @api.depends('request_ids')
    def _compute_request_count(self):
        for workflow in self:
            workflow.request_count = len(workflow.request_ids)

    @api.constrains('active', 'stage_ids')
    def _check_stages(self):
        for workflow in self:
            if workflow.active and not workflow.stage_ids:
                raise ValidationError(
                    "Un workflow actif doit contenir au moins une étape d'approbation."
                )

    def get_first_stage(self):
        self.ensure_one()
        stages = self.stage_ids.filtered('active').sorted('sequence')
        return stages[:1]

    def get_next_stage(self, current_stage):
        self.ensure_one()

        stages = self.stage_ids.filtered('active').sorted('sequence')

        for index, stage in enumerate(stages):
            if stage == current_stage and index + 1 < len(stages):
                return stages[index + 1]

        return self.env['approval.stage']

    def action_view_stages(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': "Étapes d'approbation",
            'res_model': 'approval.stage',
            'view_mode': 'list,form',
            'domain': [
                ('workflow_id', '=', self.id),
            ],
            'context': {
                'default_workflow_id': self.id,
            },
        }

    def action_view_requests(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': "Demandes d'approbation",
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('workflow_id', '=', self.id),
            ],
            'context': {
                'default_workflow_id': self.id,
            },
        }
