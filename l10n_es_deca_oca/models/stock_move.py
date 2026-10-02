# Copyright 2026 Acysos S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    weight = fields.Float(
        compute="_compute_weight",
        digits="Stock Weight",
        store=True,
        compute_sudo=True,
    )

    @api.depends("product_id", "product_uom_qty", "product_uom")
    def _compute_weight(self):
        moves_with_weight = self.filtered(lambda moves: moves.product_id.weight > 0.00)
        for move in moves_with_weight:
            move.weight = move.product_qty * move.product_id.weight
        (self - moves_with_weight).weight = 0
