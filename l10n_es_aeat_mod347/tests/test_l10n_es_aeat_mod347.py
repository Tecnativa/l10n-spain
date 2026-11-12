# Copyright 2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from typing import ClassVar

from odoo import exceptions
from odoo.fields import Command
from odoo.tests import Form

from odoo.addons.l10n_es_aeat.tests.test_l10n_es_aeat_mod_base import (
    TestL10nEsAeatModBase,
)


class TestL10nEsAeatMod347(TestL10nEsAeatModBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.state_es_m = cls.env.ref("base.state_es_m")
        cls.country_es = cls.env.ref("base.es")
        cls.customer.with_context(no_vat_validation=True).write(
            {
                "state_id": cls.state_es_m.id,
                "country_id": cls.country_es.id,
                "vat": "12345678Z",
            }
        )
        cls.supplier.with_context(no_vat_validation=True).write(
            {
                "state_id": cls.state_es_m.id,
                "country_id": cls.country_es.id,
                "vat": "87654321Z",
            }
        )
        # Create model
        cls.model347 = cls.env["l10n.es.aeat.mod347.report"].create(
            {
                "name": "9990000000347",
                "company_id": cls.company.id,
                "company_vat": "123456789",
                "contact_name": "Test owner",
                "statement_type": "N",
                "support_type": "T",
                "contact_phone": "911234455",
                "year": 2019,
                "date_start": "2019-01-01",
                "date_end": "2019-12-31",
            }
        )
        cls.customer_2 = cls.customer.copy(
            {"name": "Test customer 2", "vat": "ES12345678Z"}
        )
        cls.customer_3 = cls.customer.copy(
            {"name": "Test customer 3", "vat": "12345678Z"}
        )
        cls.customer_4 = cls.customer.copy(
            {"name": "Test customer 4", "vat": "ESB29805314"}
        )
        # TODO: Zip set is not necessary https://github.com/odoo/odoo/pull/94333
        cls.customer_5 = cls.customer.copy(
            {
                "name": "Test customer 5",
                # For testing spanish states mapping
                "country_id": cls.env.ref("base.es").id,
                "vat": "12345678Z",
                "zip": 28001,
            }
        )
        cls.customer_6 = cls.customer.copy(
            {
                "name": "Test customer 6",
                "country_id": cls.env.ref("base.es").id,
                "vat": "B29805314",
                "zip": 28001,
            }
        )
        cls.supplier_2 = cls.supplier.with_context(no_vat_validation=True).copy(
            {
                "name": "Test supplier 2",
                # partner_vat_unique compatibility: It is necessary to define the vat
                # field because if partner_vat_unique is installed, the vat field
                # will have copy=False
                "vat": cls.supplier.vat,
            }
        )
        # Invoice lower than the limit
        cls.taxes_sale = {
            "S_IVA10B": (2000, 200),
        }
        cls.invoice_1 = cls._invoice_sale_create("2019-01-01")
        # Cancelled invoice - Shouldn't count for partner `customer`
        cls.invoice_cancel = cls._invoice_sale_create("2019-01-01")
        cls.invoice_cancel.button_cancel()
        # Invoice higher than limit with IRPF
        cls.taxes_sale = {
            "S_IVA10S,S_IRPF20": (4000, 400),
        }
        cls.invoice_2 = cls._invoice_sale_create(
            "2019-04-01", {"partner_id": cls.customer_2.id}
        )
        # # Invoice higher than limit manually excluded
        cls.invoice_3 = cls._invoice_sale_create(
            "2019-01-01", {"partner_id": cls.customer_3.id, "not_in_mod347": True}
        )
        # # Invoice higher than cash limit
        cls.taxes_sale = {
            "S_IVA10S": (6000, 600),
        }
        cls.invoice_4 = cls._invoice_sale_create(
            "2019-07-01", {"partner_id": cls.customer_4.id}
        )
        # Create payment from invoice
        cls.payment_model = cls.env["account.payment.register"]
        payment_form = Form(
            cls.payment_model.with_context(
                active_model="account.move", active_ids=cls.invoice_4.ids
            )
        )
        payment_form.journal_id = cls.journal_cash
        payment_form.payment_date = "2019-07-01"
        payment_form.save().action_create_payments()
        # Invoice outside period higher than cash limit
        cls.invoice_5 = cls._invoice_sale_create(
            "2018-01-01", {"partner_id": cls.customer_5.id}
        )
        payment_form = Form(
            cls.payment_model.with_context(
                active_model="account.move", active_ids=cls.invoice_5.ids
            )
        )
        payment_form.journal_id = cls.journal_cash
        payment_form.payment_date = "2019-01-01"
        payment_form.save().action_create_payments()
        # Customer refund higher than limit
        cls.taxes_sale = {
            "S_IVA10S": (5000, 500),
        }
        cls.invoice_5 = cls._invoice_sale_create(
            "2019-01-01", {"partner_id": cls.customer_6.id, "move_type": "out_refund"}
        )
        # Purchase invoice higher than the limit
        cls.taxes_purchase = {
            "P_IVA10_SC": (3000, 300),
        }
        cls.invoice_suppler_1 = cls._invoice_purchase_create("2019-01-01")
        # Supplier refund higher than limit
        cls.taxes_purchase = {
            "P_IVA10_SC": (4000, 400),
        }
        cls.invoice_suppler_2 = cls._invoice_purchase_create(
            "2019-01-01", {"partner_id": cls.supplier_2.id, "move_type": "in_refund"}
        )

    def test_model_347(self):
        # Check flag propagation
        self.assertFalse(self.invoice_1.not_in_mod347)
        self.assertTrue(self.invoice_3.not_in_mod347)
        # Check model
        self.model347.button_calculate()
        partner_record_vals = [
            # key, partner, amount, cash_amount, 1T, 2T, 3T, 4T
            ("A", self.supplier, 3300, 0, 3300, 0, 0, 0),
            ("A", self.supplier_2, -4400, 0, -4400, 0, 0, 0),
            ("B", self.customer_2, 4400, 0, 0, 4400, 0, 0),
            ("B", self.customer_4, 6600, 6600, 0, 0, 6600, 0),
            ("B", self.customer_6, -5500, 0, -5500, 0, 0, 0),
            ("B", self.customer_5, 0, 6600, 0, 0, 0, 0),
        ]
        self.assertEqual(self.model347.total_partner_records, len(partner_record_vals))
        self.assertAlmostEqual(
            self.model347.total_amount, sum(x[2] for x in partner_record_vals)
        )
        self.assertAlmostEqual(
            self.model347.total_cash_amount, sum(x[3] for x in partner_record_vals)
        )
        for vals in partner_record_vals:
            partner_record = self.model347.partner_record_ids.filtered(
                lambda x, v=vals: x.partner_id == v[1]
            )
            self.assertEqual(partner_record.operation_key, vals[0])
            self.assertAlmostEqual(partner_record.amount, vals[2])
            self.assertAlmostEqual(partner_record.cash_amount, vals[3])
            self.assertAlmostEqual(partner_record.first_quarter, vals[4])
            self.assertAlmostEqual(partner_record.second_quarter, vals[5])
            self.assertAlmostEqual(partner_record.third_quarter, vals[6])
            self.assertAlmostEqual(partner_record.fourth_quarter, vals[7])
        # Check VAT handle
        partner_record = self.model347.partner_record_ids.filtered(
            lambda x: x.partner_id == self.customer_2
        )
        self.assertEqual(partner_record.partner_vat, "12345678Z")
        self.assertEqual(partner_record.partner_country_code, "ES")
        partner_record = self.model347.partner_record_ids.filtered(
            lambda x: x.partner_id == self.customer_4
        )
        self.assertEqual(partner_record.partner_vat, "B29805314")
        self.assertEqual(partner_record.partner_country_code, "ES")
        partner_record = self.model347.partner_record_ids.filtered(
            lambda x: x.partner_id == self.customer_5
        )
        self.assertEqual(partner_record.partner_vat, "12345678Z")
        self.assertEqual(partner_record.partner_country_code, "ES")
        partner_record = self.model347.partner_record_ids.filtered(
            lambda x: x.partner_id == self.customer_6
        )
        self.assertEqual(partner_record.partner_vat, "B29805314")
        self.assertEqual(partner_record.partner_country_code, "ES")
        # Export to BOE
        export_to_boe = self.env["l10n.es.aeat.report.export_to_boe"].create(
            {"name": "test_export_to_boe.txt"}
        )
        export_config_xml_ids = [
            "l10n_es_aeat_mod347.aeat_mod347_main_export_config",
        ]
        for xml_id in export_config_xml_ids:
            export_config = self.env.ref(xml_id)
            self.assertTrue(export_to_boe._export_config(self.model347, export_config))

    def _partner_record(self, partner, report=None):
        return (report or self.model347).partner_record_ids.filtered(
            lambda x: x.partner_id == partner
        )

    def test_partner_record_ids_states(self):
        self.model347.button_calculate()
        record_no_email = self._partner_record(self.supplier)
        self.assertFalse(self.supplier.email)
        record_email = self._partner_record(self.customer_2)
        self.customer_2.email = "test@email.com"
        self.model347.button_send_mails()
        self.assertEqual(record_no_email.state, "pending")
        self.assertEqual(record_email.state, "sent")
        self.model347.button_send_mails()
        self.assertEqual(record_no_email.state, "pending")
        self.supplier.email = "test1@email.com"
        self.model347.button_send_mails()
        self.assertEqual(record_no_email.state, "sent")

    def test_mod347_unit_report(self):
        self.model347.button_calculate()
        partner_record = self._partner_record(self.customer_2)
        self.assertTrue(partner_record.check_ok, partner_record.error_text)
        self.assertEqual(self.model347.error_count, 0)
        # The user writes a wrong state code (it must be digits)
        with Form(partner_record) as record_form:
            record_form.partner_state_code = "AA"
        self.assertFalse(partner_record.check_ok)
        # The declaration is read again, as the screen does
        self.env.invalidate_all()
        self.assertEqual(self.model347.error_count, 1)
        with self.assertRaises(exceptions.ValidationError):
            self.model347.button_confirm()
        with Form(partner_record) as record_form:
            record_form.partner_state_code = "28"
        self.assertTrue(partner_record.check_ok)
        self.model347.button_confirm()
        self.assertEqual(self.model347.state, "done")

    def test_mod347_unit_partner_record(self):
        self.model347.button_calculate()
        partner_record = self._partner_record(self.supplier)
        # Test action_exception, action_confirm, action_pending
        partner_record.action_exception()
        self.assertEqual(partner_record.state, "exception")
        partner_record.action_confirm()
        self.assertEqual(partner_record.state, "confirmed")
        partner_record.action_pending()
        self.assertEqual(partner_record.state, "pending")
        # Test action_send
        res = partner_record.action_send()
        self.assertEqual(res["res_model"], "mail.compose.message")
        # The invoice address of the partner is suggested as recipient
        invoice_contact = (
            self.env["res.partner"]
            .with_context(no_vat_validation=True)
            .create(
                {
                    "name": "Supplier invoicing",
                    "type": "invoice",
                    "parent_id": self.supplier.id,
                    "email": "invoicing@supplier.example.com",
                }
            )
        )
        recipients = partner_record._message_get_suggested_recipients()
        self.assertIn(invoice_contact.id, [r.get("partner_id") for r in recipients])
        # The partner data are loaded when the user changes the partner
        self.customer_5.country_id = self.env.ref("base.es")
        with Form(partner_record) as record_form:
            record_form.partner_id = self.customer_5
            self.assertEqual(record_form.partner_vat, "12345678Z")
            self.assertEqual(record_form.partner_state_code, "28")
        # Test button_recompute
        partner_record.partner_id = self.supplier
        partner_record.button_recompute()
        self.assertAlmostEqual(partner_record.amount, 3300)
        self._invoice_purchase_create("2019-01-01")
        partner_record.button_recompute()
        self.assertAlmostEqual(partner_record.amount, 7700)

    def test_mod347_unit_real_estate_record(self):
        self.customer_5.state_id = self.state_es_m
        real_estate_form = Form(
            self.env["l10n.es.aeat.mod347.real_estate_record"].with_context(
                default_report_id=self.model347.id
            )
        )
        real_estate_form.partner_id = self.customer_5
        real_estate_form.situation = "1"
        self.assertEqual(real_estate_form.partner_vat, "12345678Z")
        self.assertEqual(real_estate_form.state_code, "28")
        real_estate = real_estate_form.save()
        self.assertTrue(real_estate.check_ok)
        real_estate.state_code = False
        self.assertFalse(real_estate.check_ok)

    def test_mod347_real_estate_record_foreign_partner(self):
        foreign_partner = (
            self.env["res.partner"]
            .with_context(no_vat_validation=True)
            .create(
                {
                    "name": "Foreign landlord",
                    "country_id": self.env.ref("base.fr").id,
                    "vat": "FR23334175221",
                }
            )
        )
        real_estate_form = Form(
            self.env["l10n.es.aeat.mod347.real_estate_record"].with_context(
                default_report_id=self.model347.id
            )
        )
        with self.assertRaises(exceptions.ValidationError):
            real_estate_form.partner_id = foreign_partner

    def test_mod347_partner_record_from_list(self):
        """A record created from the "Partner records" button belongs to the
        declaration."""
        action = self.model347.btn_list_records()
        record_form = Form(
            self.env[action["res_model"]].with_context(**action["context"])
        )
        record_form.partner_id = self.customer
        record_form.operation_key = "B"
        record = record_form.save()
        self.assertEqual(record.report_id, self.model347)
        self.assertIn(record, self.model347.partner_record_ids)

    def test_mod347_unit_move_record(self):
        # Test _default_partner_record
        self.model347.button_calculate()
        partner_record = self.model347.partner_record_ids[0]
        move_record = (
            self.env["l10n.es.aeat.mod347.move.record"]
            .with_context(partner_record_id=partner_record.id)
            .create(
                {
                    "move_id": self.invoice_1.id,
                    "amount": 100.0,
                }
            )
        )
        self.assertEqual(move_record.partner_record_id, partner_record)

    def test_mod347_unit_wizard_send_mail(self):
        self.model347.button_calculate()
        partner_record = self._partner_record(self.customer_2)
        self.assertEqual(partner_record.state, "pending")
        action = partner_record.action_send()
        composer_form = Form(
            self.env[action["res_model"]].with_context(
                active_id=partner_record.id,
                active_ids=partner_record.ids,
                **action["context"],
            ),
            view=self.env["ir.ui.view"].browse(action["view_id"]),
        )
        composer_form.body = "Test body"
        composer_form.save().action_send_mail()
        self.assertEqual(partner_record.state, "sent")

    def test_mod347_cash_other_company(self):
        """Cash collected by another company of the user is not declared."""
        company_2 = self.env["res.company"].sudo().create({"name": "Company 2"})
        self.env["account.chart.template"].sudo()._load(
            template_code="es_pymes", company=company_2, install_demo=False
        )
        self.env.user.sudo().company_ids |= company_2
        env_2 = self.env(
            context=dict(
                self.env.context,
                company_id=company_2.id,
                allowed_company_ids=[company_2.id, self.company.id],
            )
        )
        cash_journal = env_2["account.journal"].create(
            {"name": "Cash 2", "code": "CSH2", "type": "cash"}
        )
        receivable = env_2["account.account"].search(
            [
                ("company_ids", "=", company_2.id),
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        move = env_2["account.move"].create(
            {
                "company_id": company_2.id,
                "journal_id": cash_journal.id,
                "date": "2019-05-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": cash_journal.default_account_id.id,
                            "debit": 7000,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": receivable.id,
                            "partner_id": self.customer_2.id,
                            "credit": 7000,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        self.model347.with_context(
            allowed_company_ids=(self.company | company_2).ids
        ).button_calculate()
        partner_record = self._partner_record(self.customer_2)
        self.assertAlmostEqual(partner_record.amount, 4400)
        self.assertAlmostEqual(partner_record.cash_amount, 0)
        self.assertAlmostEqual(self.model347.total_cash_amount, 13200)

    def test_mod347_boe_export(self):
        self.model347.button_calculate()
        self.model347.button_confirm()
        # "Export to BOE" button of the declaration
        wizard = (
            self.env["l10n.es.aeat.report.export_to_boe"]
            .with_context(active_id=self.model347.id, active_model=self.model347._name)
            .create({})
        )
        wizard.action_get_file()
        content = (
            self.env["ir.attachment"]
            .search(
                [
                    ("res_model", "=", self.model347._name),
                    ("res_id", "=", self.model347.id),
                ]
            )
            .raw.decode("iso-8859-1")
        )
        records = [content[i : i + 500] for i in range(0, len(content), 500)]
        self.assertEqual(records[0][:4], "1347")
        partner_records = [r for r in records[1:] if r[0] == "2"]
        self.assertEqual(len(partner_records), 6)
        # Positions 18-26 partner NIF, 82 operation key, 83-98 annual amount
        record = next(
            r for r in partner_records if r[35:75].upper().startswith("TEST CUSTOMER 2")
        )
        self.assertEqual(record[1:8], "3472019")
        self.assertEqual(record[17:26], "12345678Z")
        self.assertEqual(record[81], "B")
        self.assertEqual(record[82:98], " 000000000440000")
        record = next(
            r for r in partner_records if r[35:75].upper().startswith("TEST CUSTOMER 6")
        )
        self.assertEqual(record[82:98], "N000000000550000")


class TestL10nEsAeatMod347CoreTaxes(TestL10nEsAeatModBase):
    """Taxes of the Odoo core chart that the model did not include before."""

    taxes_sale: ClassVar[dict] = {
        "S_IVA5B": (3000, 150),
        "S_IVA0B": (1000, 0),
    }
    taxes_purchase: ClassVar[dict] = {
        "P_IVA5_BI": (3200, 160),
    }

    def test_model_347_core_taxes(self):
        for partner in self.customer | self.supplier:
            partner.with_context(no_vat_validation=True).write(
                {
                    "state_id": self.env.ref("base.state_es_m").id,
                    "country_id": self.env.ref("base.es").id,
                    "vat": "12345678Z" if partner == self.customer else "87654321Z",
                }
            )
        self._invoice_sale_create("2024-02-01")
        self._invoice_purchase_create("2024-02-01")
        model347 = self.env["l10n.es.aeat.mod347.report"].create(
            {
                "name": "9990000001347",
                "company_id": self.company.id,
                "company_vat": "123456789",
                "contact_name": "Test owner",
                "statement_type": "N",
                "support_type": "T",
                "contact_phone": "911234455",
                "year": 2024,
                "date_start": "2024-01-01",
                "date_end": "2024-12-31",
            }
        )
        model347.button_calculate()
        for key, partner, amount in (
            ("B", self.customer, 4150),
            ("A", self.supplier, 3360),
        ):
            record = model347.partner_record_ids.filtered(
                lambda x, partner=partner: x.partner_id == partner
            )
            self.assertEqual(record.operation_key, key)
            self.assertAlmostEqual(record.amount, amount, 2)


class TestL10nEsAeatMod347Exclusions(TestL10nEsAeatModBase):
    """Operations that the 347 does not declare."""

    def _create_report(self):
        return self.env["l10n.es.aeat.mod347.report"].create(
            {
                "name": "9990000002347",
                "company_id": self.company.id,
                "company_vat": "123456789",
                "contact_name": "Test owner",
                "statement_type": "N",
                "support_type": "T",
                "contact_phone": "911234455",
                "year": 2024,
                "date_start": "2024-01-01",
                "date_end": "2024-12-31",
            }
        )

    def _partner(self, name, vat):
        return (
            self.env["res.partner"]
            .with_context(no_vat_validation=True)
            .create(
                {
                    "name": name,
                    "state_id": self.env.ref("base.state_es_m").id,
                    "country_id": self.env.ref("base.es").id,
                    "vat": vat,
                    "property_account_payable_id": self.accounts["410000"].id,
                    "property_account_receivable_id": self.accounts["430000"].id,
                }
            )
        )

    def _invoice(self, move_type, partner, tax_code, amount):
        account = self.accounts["700000" if move_type == "out_invoice" else "600000"]
        journal = (
            self.journal_sale if move_type == "out_invoice" else self.journal_purchase
        )
        move = (
            self.env["account.move"]
            .with_user(self.billing_user)
            .create(
                {
                    "company_id": self.company.id,
                    "move_type": move_type,
                    "partner_id": partner.id,
                    "journal_id": journal.id,
                    "invoice_date": "2024-03-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": tax_code,
                                "account_id": account.id,
                                "price_unit": amount,
                                "tax_ids": [Command.set(self._get_taxes(tax_code).ids)],
                            }
                        )
                    ],
                }
            )
        )
        move.action_post()
        return move

    def test_map_lines_match_company_taxes(self):
        """Every tax of the keys exists in the Odoo core chart, and no key adds
        withholdings, imports (DUA) or not subject purchases."""
        for key, xmlid in (
            ("A", "l10n_es_aeat_mod347.aeat_mod347_map_a"),
            ("B", "l10n_es_aeat_mod347.aeat_mod347_map_b"),
        ):
            map_line = self.env.ref(xmlid)
            taxes = map_line.get_taxes_for_company(self.company)
            self.assertEqual(len(taxes), len(map_line.tax_xmlid_ids), key)
            excluded = {"dua", "retencion"}
            if key == "A":
                excluded |= {"no_sujeto", "no_sujeto_loc"}
            self.assertFalse(
                taxes.filtered(lambda t, excluded=excluded: t.l10n_es_type in excluded),
                key,
            )

    def test_excluded_operations(self):
        supplier = self._partner("Supplier excluded", "87654321X")
        customer = self._partner("Customer export", "12345678Z")
        # Not subject purchases, intra-community acquisitions and imports
        for tax_code in ("P_IVA0_NS", "P_IVA21_IC_BC", "P_IVA21_IBC_GROUP"):
            self._invoice("in_invoice", supplier, tax_code, 7000)
        # Exports
        self._invoice("out_invoice", customer, "S_IVA0_G_E", 7000)
        report = self._create_report()
        report.button_calculate()
        self.assertFalse(report.partner_record_ids)

    def test_sale_s_iva_e(self):
        """Sales with s_iva_e are declared in key B, as in 18.0 and 19.0."""
        customer = self._partner("Customer s_iva_e", "12345678Z")
        self._invoice("out_invoice", customer, "S_IVA_E", 7000)
        report = self._create_report()
        report.button_calculate()
        self.assertEqual(report.partner_record_ids.operation_key, "B")
        self.assertAlmostEqual(report.partner_record_ids.amount, 7000)
