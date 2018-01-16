# -*- coding: utf-8 -*-
# Copyright 2017 Luis M. Ontalba <luis.martinez@tecnativa.com>
# Copyright 2017 - Eficent Business and IT Consulting Services, S.L.
#                  <contact@eficent.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openerp import api, fields, models


class AccountMoveLine(models.Model):
    """Inheritance of account move line to add some fields:
    - AEAT_349_operation_key: Operation key of invoice line
    """
    _inherit = 'account.move.line'

    aeat_349_operation_key = fields.Many2one(
        string='AEAT 349 Operation key',
        comodel_name='aeat.349.map.line',
        compute='_compute_aeat_349_operation_key',
        store=True,
    )

    @api.depends('tax_ids')
    def _compute_aeat_349_operation_key(self):
        for line in self:
            if line.tax_ids:
                taxes = line.mapped('tax_ids').filtered(
                    lambda x: x.aeat_349_operation_key)
                if taxes:
                    line.aeat_349_operation_key = \
                        taxes[0].aeat_349_operation_key
