# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ApprovalDashboard(models.Model):
    """Tableau de bord décisionnel du moteur d'approbation.

    Ce modèle ne représente pas une donnée métier à proprement parler :
    c'est un enregistrement 'singleton' (un seul existe réellement,
    cf. get_dashboard()) dont tous les champs sont calculés à la volée
    à partir de approval.request et approval.history, afin de refléter
    l'état réel du système à chaque ouverture, sans risque de données
    figées ou désynchronisées.
    """
    _name = 'approval.dashboard'
    _description = "Tableau de bord des approbations"

    name = fields.Char(default="Tableau de bord", readonly=True)

    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company,
    )

    # --- KPI globaux --------------------------------------------------
    total_count = fields.Integer(
        string="Total des demandes", compute='_compute_kpis',
    )
    pending_count = fields.Integer(
        string="En attente", compute='_compute_kpis',
    )
    approved_count = fields.Integer(
        string="Approuvées", compute='_compute_kpis',
    )
    refused_count = fields.Integer(
        string="Refusées", compute='_compute_kpis',
    )
    draft_count = fields.Integer(
        string="Brouillons", compute='_compute_kpis',
    )
    avg_validation_hours = fields.Float(
        string="Temps moyen de validation (heures)",
        compute='_compute_kpis',
        help="Durée moyenne, en heures, entre la soumission et "
             "l'approbation finale des demandes déjà approuvées.",
    )

    # --- Répartitions (affichées sous forme de texte / graphes dans
    # les vues, calculées via read_group) --------------------------
    category_stats = fields.Text(
        string="Statistiques par catégorie", compute='_compute_kpis',
    )
    department_stats = fields.Text(
        string="Statistiques par département", compute='_compute_kpis',
    )
    monthly_stats = fields.Text(
        string="Statistiques par mois", compute='_compute_kpis',
    )

    @api.depends('company_id')
    def _compute_kpis(self):
        Request = self.env['approval.request']
        for dashboard in self:
            domain = [('company_id', '=', dashboard.company_id.id)]

            dashboard.total_count = Request.search_count(domain)
            dashboard.pending_count = Request.search_count(
                domain + [('state', '=', 'in_progress')]
            )
            dashboard.approved_count = Request.search_count(
                domain + [('state', '=', 'approved')]
            )
            dashboard.refused_count = Request.search_count(
                domain + [('state', '=', 'refused')]
            )
            dashboard.draft_count = Request.search_count(
                domain + [('state', '=', 'draft')]
            )

            dashboard.avg_validation_hours = dashboard._compute_avg_validation_hours(domain)
            dashboard.category_stats = dashboard._compute_category_stats(domain)
            dashboard.department_stats = dashboard._compute_department_stats(domain)
            dashboard.monthly_stats = dashboard._compute_monthly_stats(domain)

    def _compute_avg_validation_hours(self, domain):
        """Calcule la durée moyenne (en heures) entre la création et
        la dernière modification des demandes approuvées, en
        s'appuyant sur l'historique d'audit (action 'submit' vs
        'approve') pour plus de précision que create_date/write_date.
        """
        requests = self.env['approval.request'].search(
            domain + [('state', '=', 'approved')]
        )
        if not requests:
            return 0.0

        durations = []
        for request in requests:
            submit_entry = request.history_ids.filtered(
                lambda h: h.action == 'submit'
            ).sorted('date')[:1]
            approve_entry = request.history_ids.filtered(
                lambda h: h.action == 'approve'
            ).sorted('date', reverse=True)[:1]
            if submit_entry and approve_entry:
                delta = approve_entry.date - submit_entry.date
                durations.append(delta.total_seconds() / 3600.0)

        return sum(durations) / len(durations) if durations else 0.0

    def _compute_category_stats(self, domain):
        results = self.env['approval.request'].read_group(
            domain, ['category_id'], ['category_id'],
        )
        lines = [
            f"{r['category_id'][1] if r['category_id'] else 'Non classé'} : "
            f"{r['category_id_count']}"
            for r in results
        ]
        return "\n".join(lines)

    def _compute_department_stats(self, domain):
        results = self.env['approval.request'].read_group(
            domain, ['department_id'], ['department_id'],
        )
        lines = [
            f"{r['department_id'][1] if r['department_id'] else 'Non classé'} : "
            f"{r['department_id_count']}"
            for r in results
        ]
        return "\n".join(lines)

    def _compute_monthly_stats(self, domain):
        results = self.env['approval.request'].read_group(
            domain, ['create_date'], ['create_date:month'],
        )
        lines = [
            f"{r['create_date:month']} : {r['__count']}"
            for r in results
        ]
        return "\n".join(lines)

    # ---------------------------------------------------------------
    # Accès singleton + actions de drill-down
    # ---------------------------------------------------------------
    @api.model
    def get_dashboard(self):
        """Retourne l'enregistrement unique de tableau de bord pour la
        société courante, en le créant s'il n'existe pas encore.
        Utilisé comme point d'entrée par l'action de menu.
        """
        dashboard = self.search(
            [('company_id', '=', self.env.company.id)], limit=1,
        )
        if not dashboard:
            dashboard = self.create({'company_id': self.env.company.id})
        return dashboard

    def action_view_pending(self):
        self.ensure_one()
        return self._action_view_requests(
            "Demandes en attente", [('state', '=', 'in_progress')],
        )

    def action_view_approved(self):
        self.ensure_one()
        return self._action_view_requests(
            "Demandes approuvées", [('state', '=', 'approved')],
        )

    def action_view_refused(self):
        self.ensure_one()
        return self._action_view_requests(
            "Demandes refusées", [('state', '=', 'refused')],
        )

    def _action_view_requests(self, title, extra_domain):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)] + extra_domain,
        }