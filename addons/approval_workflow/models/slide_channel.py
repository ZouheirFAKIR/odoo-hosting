# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class SlideChannel(models.Model):
    """Intégration du moteur AWE sur les cours eLearning (module
    website_slides).

    Comme pour les autres intégrations, ce module ne réimplémente
    aucune logique de workflow ici : il se contente de fournir à AWE
    (`approval.request.create_for_document`) les informations
    pertinentes du cours. Le moteur AWE reste seul responsable de la
    sélection du workflow. slide.channel reste propriétaire de son
    propre cycle de vie (publication, etc.), qui n'est jamais modifié
    par ce module.

    Limites assumées (absence d'équivalent direct dans slide.channel) :
    - `training_type` est fixé à 'online', un cours eLearning étant
      par nature une formation en ligne ;
    - aucun `vendor_id` (organisme) n'est transmis : le responsable du
      cours (`user_id`, un res.users) n'est pas un res.partner et ne
      peut donc pas être assigné directement à ce champ ;
    - aucune date de début/fin ni coût n'existe nativement sur
      slide.channel : ces champs restent vides sur la demande créée
      et peuvent être complétés manuellement si nécessaire.
    """

    _inherit = 'slide.channel'

    approval_request_id = fields.Many2one(
        'approval.request',
        string="Demande d'approbation AWE",
        readonly=True,
        copy=False,
        help='Demande d\'approbation AWE liée à ce cours, si une '
             'validation a été demandée.',
    )

    awe_approval_state = fields.Selection(
        related='approval_request_id.state',
        string="Statut d'approbation AWE",
        readonly=True,
        store=False,
    )

    awe_training_state = fields.Selection(
        [
            ('to_confirm', 'À confirmer'),
            ('confirmed', 'Confirmée'),
            ('cancelled', 'Annulée'),
        ],
        string='Statut de la demande de formation',
        default='to_confirm',
        copy=False,
        tracking=True,
        help="État de la demande de formation liée à ce cours, piloté "
             "par le moteur AWE. Champ dédié à AWE : slide.channel ne "
             "possède nativement aucun état 'Confirmed'/'Cancelled' "
             "pour une demande de formation (son propre `state` gère "
             "la publication du cours et n'est jamais touché ici).",
    )

    def action_submit_for_approval(self):
        """Bouton 'Submit for Approval' sur le cours eLearning.

        Toute la logique de création/soumission reste dans AWE
        (`approval.request.create_for_document`) — ce module se
        contente de fournir les champs pertinents du cours.
        """
        self.ensure_one()

        if self.approval_request_id and self.approval_request_id.state \
                not in ('approved', 'refused', 'cancelled'):
            raise UserError(
                "Une demande d'approbation est déjà en cours pour ce "
                "cours : %s." % self.approval_request_id.name
            )

        request = self.env['approval.request'].create_for_document(
            self,
            'TRAINING_REQUEST',
            extra_vals={
                'training_name': self.name,
                'training_type': 'online',
                'description': html2plaintext(self.description or ''),
                'justification': (
                    'Demande de formation liée au cours eLearning : %s.'
                    % self.name
                ),
            },
        )

        self.approval_request_id = request

        return True

    def action_view_approval_request(self):
        """Smart button : ouvre la approval.request liée à ce
        cours."""
        self.ensure_one()

        if not self.approval_request_id:
            raise UserError("Aucune demande d'approbation liée à "
                             "ce cours.")

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
    # / refusal_action_method (configurés sur cat_training).
    #
    # BUG CORRIGÉ : ces deux méthodes n'existaient pas du tout sur ce
    # modèle, et la catégorie 'cat_training' ne renseignait même pas
    # final_action_method / refusal_action_method. _run_final_action()
    # fait donc juste `continue` silencieusement (aucune erreur,
    # aucune action) : c'est la cause exacte du blocage observé sur
    # Formation. slide.channel n'a pas d'équivalent natif Odoo pour
    # une transition "Confirmed"/"Cancelled" de demande de formation
    # (son `state` natif gère uniquement la publication du cours) :
    # on pilote donc le champ dédié `awe_training_state` ci-dessus,
    # jamais le `state` natif de slide.channel.
    # ============================================================

    def action_awe_approve(self):
        """Confirme la demande de formation une fois l'approbation
        finale AWE atteinte. N'a aucun effet si déjà confirmée ou
        annulée (idempotence)."""
        for channel in self:
            if channel.awe_training_state not in (
                'confirmed',
                'cancelled',
            ):
                channel.awe_training_state = 'confirmed'
        return True

    def action_awe_refuse(self):
        """Annule la demande de formation lorsque l'approbation AWE
        est refusée. N'a aucun effet si déjà confirmée ou annulée
        (idempotence)."""
        for channel in self:
            if channel.awe_training_state not in (
                'confirmed',
                'cancelled',
            ):
                channel.awe_training_state = 'cancelled'
        return True