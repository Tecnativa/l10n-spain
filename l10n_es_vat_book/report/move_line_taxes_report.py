# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _name = "account.move.line.taxes.report"
    _description = "Account move line taxes"
    _auto = False
    _rec_name = 'invoice_id'
    # _order = 'date desc'

    # tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    tax_line_id = fields.Many2one(
        comodel_name='account.tax',
        string='Originator tax',
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        readonly=True,
        auto_join=True,
    )
    invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string="Invoice",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        readonly=True,
    )
    date = fields.Datetime(
        string='Date Order',
        readonly=True,
    )

    def _select(self):
        select_str = """
            SELECT tax_line_id,
                taxes,
                move_id,
                invoice_id,
                partner_id,
                MAX(date) AS date,
                SUM(credit) AS credit,
                SUM(debit) AS debit,
                array_agg(id) AS lines
        """
        return select_str

    def _from(self):
        from_str = """
            SELECT aml.tax_line_id,
                aml.move_id,
                aml.invoice_id,
                aml.partner_id,
                aml.date,
                aml.id,
                aml.credit,
                aml.debit,
                (select array_agg(amlat.account_tax_id) AS taxes
                    FROM account_move_line_account_tax_rel amlat
                    WHERE aml.id = amlat.account_move_line_id
                ) AS taxes
            FROM account_move_line aml
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY tax_line_id,
                taxes,
                move_id,
                invoice_id,
                partner_id
        """
        return group_by_str

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s ) sub
            %s
            )""" % (
        self._table, self._select(), self._from(), self._group_by()))
