# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon


class TestL10nEsAtc(BaseCommon):
    """The module is the glue every ATC declaration sits on: it adds the ATC
    menu, the public way of the company and the helpers that turn Odoo data
    into what the ATC files expect. Generating a declaration file is covered by
    the tests of l10n_es_atc_mod417, mod420 and mod425.
    """

    _test_user_groups = (
        "base.group_user",
        "account.group_account_manager",
        "l10n_es_aeat.group_account_aeat",
        "l10n_es_atc.group_account_atc",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.atc_report = cls.env["l10n.es.atc.report"]
        cls.atc_menu = cls.env.ref("l10n_es_atc.menu_root_atc")
        cls.atc_group = cls.env.ref("l10n_es_atc.group_account_atc")

    def test_atc_menu_hangs_under_aeat_and_is_restricted(self):
        """The ATC entry hangs under the AEAT one and is reserved to its group.

        It carries no action of its own, so the web client shows it only once a
        declaration module adds a child with an action under it.
        """
        self.assertEqual(
            self.atc_menu.parent_id, self.env.ref("l10n_es_aeat.menu_root_aeat")
        )
        self.assertIn(self.atc_group, self.atc_menu.group_ids)
        self.assertFalse(self.atc_menu.action)
        # An accountant without the ATC group never reaches it, whichever
        # declaration modules are installed
        other_accountant = self._test_user.sudo().copy(
            {"login": "accountant-without-atc"}
        )
        other_accountant.group_ids -= self.atc_group
        self.assertNotIn(
            self.atc_menu,
            self.env["ir.ui.menu"]
            .with_user(other_accountant)
            .search([])
            ._filter_visible_menus(),
        )

    def test_company_public_way_is_filled_on_the_aeat_page(self):
        """The public way is the ATC field of the company, next to its AEAT data."""
        company = self.env.company
        company.sudo().atc_public_way = "CL"
        self.assertEqual(company.atc_public_way, "CL")
        view = self.env.ref("l10n_es_atc.view_res_company_form")
        arch = company.get_view(view.id, "form")["arch"]
        self.assertIn('name="atc_public_way"', arch)

    def test_canary_province_codes_of_the_declarations(self):
        """Every ATC file identifies the province by its ATC code, not the state."""
        self.assertEqual(
            self.atc_report._atc_get_country_state_code(
                self.env.ref("base.state_es_gc")
            ),
            "35",
        )
        self.assertEqual(
            self.atc_report._atc_get_country_state_code(
                self.env.ref("base.state_es_tf")
            ),
            "38",
        )

    def test_a_state_outside_the_mapping_is_refused(self):
        """A company in a state the ATC does not know stops the declaration."""
        foreign_state = (
            self.env["res.country.state"]
            .sudo()
            .create(
                {
                    "name": "Test state",
                    "code": "ZZ",
                    "country_id": self.env.ref("base.fr").id,
                }
            )
        )
        with self.assertRaisesRegex(UserError, "state code is not mapped"):
            self.atc_report._atc_get_country_state_code(foreign_state)

    def test_amounts_are_written_in_cents(self):
        """The ATC files carry amounts without a decimal separator."""
        self.assertEqual(self.atc_report._format_amount(1234.56), 123456)
        self.assertEqual(self.atc_report._format_amount(-78.39), -7839)
        self.assertEqual(self.atc_report._format_amount(0.0), 0)
