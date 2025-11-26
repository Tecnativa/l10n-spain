# Copyright 2025 Tecnativa - Christian Ramos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class AccountUpdateVatProrate(models.TransientModel):
    _name = "account.update.vat_prorate"
    _description = "Account Update Vat Prorate"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    with_vat_prorate = fields.Boolean(
        string="With VAT Prorate",
        help=(
            "If this option is enabled, all invoice lines with VAT " "will be prorated"
        ),
    )
    vat_prorate_ids = fields.Many2many(
        "res.company.vat.prorate",
        domain="[('company_id', '=', company_id)]",
    )
    prorrate_asset_account_id = fields.Many2one(
        "account.account",
        domain="[('company_id', '=', company_id)]",
        compute="_compute_prorrate_accounts",
        store=True,
        readonly=False,
    )
    prorrate_investment_account_id = fields.Many2one(
        "account.account",
        domain="[('company_id', '=', company_id)]",
        compute="_compute_prorrate_accounts",
        store=True,
        readonly=False,
    )

    @api.model
    def default_get(self, field_list):
        res = super(AccountUpdateVatProrate, self).default_get(field_list)
        company = self.env.company
        res.update(
            {
                "company_id": company.id,
                "with_vat_prorate": company.with_vat_prorate,
                "vat_prorate_ids": [fields.Command.set(company.vat_prorate_ids.ids)],
                "prorrate_asset_account_id": (company.prorrate_asset_account_id.id),
                "prorrate_investment_account_id": (
                    company.prorrate_investment_account_id.id
                ),
            }
        )
        return res

    @api.onchange("company_id")
    def _compute_prorrate_accounts(self):
        for record in self:
            company = record.company_id
            record.update(
                {
                    "company_id": company.id,
                    "with_vat_prorate": company.with_vat_prorate,
                    "vat_prorate_ids": [
                        fields.Command.set(company.vat_prorate_ids.ids)
                    ],
                    "prorrate_asset_account_id": (company.prorrate_asset_account_id.id),
                    "prorrate_investment_account_id": (
                        company.prorrate_investment_account_id.id
                    ),
                }
            )

    def _check_execute_allowed(self):
        self.ensure_one()
        has_adviser_group = self.env.user.has_group("account.group_account_manager")
        if not (has_adviser_group or self.env.uid == SUPERUSER_ID):
            raise ValidationError(_("You are not allowed to execute this action."))

    def execute(self):
        self.ensure_one()
        self._check_execute_allowed()
        # Unlink vat prorates not in the wizard as they have been removed
        self.env["res.company.vat.prorate"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("id", "not in", self.vat_prorate_ids.ids),
            ]
        ).unlink()
        sudo_company = self.company_id.sudo()
        sudo_company.write(
            {
                "with_vat_prorate": self.with_vat_prorate,
                "prorrate_asset_account_id": (self.prorrate_asset_account_id.id),
                "prorrate_investment_account_id": (
                    self.prorrate_investment_account_id.id
                ),
            }
        )
        sudo_company._compute_prorrate_accounts()
