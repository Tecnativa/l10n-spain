# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon

IGIC_TAXES = [
    "account_tax_template_igic_sop_0_s",
    "account_tax_template_igic_sop_3_s",
    "account_tax_template_igic_sop_5_s",
    "account_tax_template_igic_sop_7_s",
    "account_tax_template_igic_sop_9_5_s",
    "account_tax_template_igic_sop_15_s",
    "account_tax_template_igic_sop_20_s",
    "account_tax_template_igic_ISP5",
]


class TestL10nEsAeatIgicApplicability(BaseCommon):
    """The IGIC taxes that Odoo core leaves without applicability get the one of
    the Canary Islands."""

    _test_user_groups = ("base.group_user", "account.group_account_manager")

    @classmethod
    def setup_independent_company(cls, **kwargs):
        return cls.env["res.company"].create(
            {
                "name": "Canary test company",
                "country_id": cls.env.ref("base.es").id,
                "state_id": cls.env.ref("base.state_es_gc").id,
            }
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["account.chart.template"]._load(
            template_code="es_pymes", company=cls.company, install_demo=False
        )
        cls.chart = cls.env["account.chart.template"].with_company(cls.company)

    def _igic_taxes(self):
        return self.env["account.tax"].concat(
            self.chart.ref(xml_id) for xml_id in IGIC_TAXES
        )

    def test_chart_of_accounts(self):
        """A company of the Canary Islands that loads the Spanish chart gets these
        taxes for the IGIC and active, as the other IGIC taxes, instead of
        inactive and taken for VAT."""
        taxes = self._igic_taxes()
        self.assertRecordValues(
            taxes, [{"l10n_es_applicability": "03", "active": True}] * 8
        )
