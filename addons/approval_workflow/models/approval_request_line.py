# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ApprovalRequestLine(models.Model):
    """Ligne de produit rattachée à une demande d'approbation.

    Utilisée lorsqu'une catégorie est configurée avec
    `use_product_lines = True` (Configuration > Catégories). Au lieu
    d'une description libre et d'un montant saisi manuellement, le
    demandeur choisit un vrai produit du catalogue (module `product`),
    et le prix/les détails proviennent de cette fiche produit.

    Exemple : catégorie « Achat » -> le demandeur sélectionne
    « Adobe Photoshop - Licence annuelle » dans la liste des produits,
    fixe une quantité, et le sous-total de la ligne alimente
    automatiquement le montant de la demande.
    """

    _name = 'approval.request.line'
    _description = "Ligne de produit de la demande d'approbation"

    request_id = fields.Many2one(
        'approval.request',
        string='Demande',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
    )

    description = fields.Char(
        string='Description',
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unité de mesure',
    )

    quantity = fields.Float(
        string='Quantité',
        default=1.0,
        required=True,
    )

    price_unit = fields.Float(
        string='Prix unitaire',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )

    subtotal = fields.Monetary(
        string='Sous-total',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.name
                line.product_uom_id = line.product_id.uom_id
                line.price_unit = line.product_id.list_price
