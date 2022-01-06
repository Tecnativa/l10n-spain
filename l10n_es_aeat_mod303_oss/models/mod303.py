# Copyright 2021 PESOL - Angel Moya
# Copyright 2021 FactorLibre - Rodrigo Bonilla <rodrigo.bonilla@factorlibre.com>
# Copyright 2021 Tecnativa - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from openerp import api, models


class L10nEsAeatMod303Report(models.Model):
    _inherit = "l10n.es.aeat.mod303.report"

    @api.multi
    def _get_tax_code_lines(self, codes, periods=None, include_children=True):
        """Populate OSS codes for the corresponding field numbers, but only for
        last period reports and when exonerated of presenting model 390 and
        having volume operations.
        """
        field_number = self.env.context.get("field_number", 0)
        if (
                field_number == 123 or (
                    field_number == 126
                    and self.period_type in ("4T", "12")
                    and self.exonerated_390 == "1"
                    and self.has_operation_volume
                )
        ):
            taxes = self.env["account.tax"].search(
                [
                    ("oss_country_id", "!=", False),
                    ("company_id", "=", self.company_id.id),
                ]
            )
            codes = (
                taxes.mapped("base_code_id") + taxes.mapped("ref_base_code_id")
            )
        return super(L10nEsAeatMod303Report, self)._get_tax_code_lines(
            codes, periods=periods, include_children=include_children,
        )

    @api.multi
    def _get_move_line_domain(self, codes, periods=None,
                              include_children=True):
        """Change dates to full year when the summary on last report of the year
        for the corresponding fields. Only field number is checked as the
        complete check for not bringing results is done on `_get_tax_lines`.
        """
        field_number = self.env.context.get("field_number", 0)
        if field_number in {126, 127}:
            periods = self.fiscalyear_id.period_ids.filtered(
                lambda x: not x.special
            )
        return super(L10nEsAeatMod303Report, self)._get_move_line_domain(
            codes, periods=periods, include_children=include_children
        )
