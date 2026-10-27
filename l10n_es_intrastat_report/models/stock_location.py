# Copyright 2009-2017 Noviat.
# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.fields import Domain


class StockLocation(models.Model):
    _inherit = "stock.location"

    intrastat_state_id = fields.Many2one(
        comodel_name="res.country.state",
        compute="_compute_intrastat_state_id",
        help="State of the address of the first warehouse (by sequence) whose "
        "stock location contains this location.",
    )

    @api.depends("parent_path")
    def _compute_intrastat_state_id(self):
        # One search for all the locations of the prefetch set (the receipt
        # locations of every line of a declaration)
        warehouses = self.env["stock.warehouse"].search(
            Domain("lot_stock_id", "parent_of", self.ids)
            & Domain("partner_id.state_id", "!=", False)
        )
        self.intrastat_state_id = False
        for location in self:
            if not location.parent_path:
                continue
            path = set(location.parent_path.split("/")[:-1])
            for warehouse in warehouses:
                if str(warehouse.lot_stock_id.id) in path:
                    location.intrastat_state_id = warehouse.partner_id.state_id
                    break

    def _get_intrastat_state(self):
        if not self:
            return False
        return self.intrastat_state_id
