# Copyright 2021 Tecnativa - João Marques
# Copyright 2022 Tecnativa - Víctor Martínez

from datetime import datetime

from odoo import _
from odoo.tests.common import Form, SavepointCase


class TestL10nIntraStatReport(SavepointCase):
    @classmethod
    def _create_invoice(cls, inv_type, partner, product=None):
        product = product or cls.product
        move_form = Form(cls.env["account.move"].with_context(default_type=inv_type))
        move_form.ref = "ABCDE"
        move_form.partner_id = partner
        move_form.partner_shipping_id = partner
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = "test"
            line_form.quantity = 1.0
            line_form.product_id = product
            line_form.price_unit = 100
        inv = move_form.save()
        inv.post()
        return inv

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set current company to Spanish
        cls.env.user.company_id.country_id = cls.env.ref("base.es").id
        # Create Intrastat partners
        cls.partner_1 = cls.env["res.partner"].create(
            {"name": "Test Partner FR", "country_id": cls.env.ref("base.fr").id}
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {"name": "Test Partner PT", "country_id": cls.env.ref("base.pt").id}
        )
        # Import Intrastat data
        cls.env["l10n.es.intrastat.code.import"].create({}).execute()
        # Create product ans assign random HS Code
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "hs_code_id": cls.env["hs.code"].browse(1).id,
                "origin_country_id": cls.env.ref("base.fr").id,
            }
        )
        # Invoices to be used in dispatches
        cls.invoices = {
            "dispatches": {
                "invoices": [],
                cls.partner_1.country_id: 0,
                cls.partner_2.country_id: 0,
            },
            "arrivals": {
                "invoices": [],
                cls.partner_1.country_id: 0,
                cls.partner_2.country_id: 0,
            },
        }
        for inv_type in ("out_invoice", "in_refund", "in_invoice", "out_refund"):
            declaration_type = (
                "dispatches" if inv_type in ("out_invoice", "in_refund") else "arrivals"
            )
            for partner in (cls.partner_1, cls.partner_2):
                invoice = cls._create_invoice(inv_type, partner)
                cls.invoices[declaration_type]["invoices"].append(invoice)
                cls.invoices[declaration_type][partner.country_id] += 1

    def _check_move_lines_present(self, original, target):
        for move in original:
            for line in move.invoice_line_ids:
                self.assertTrue(line in target.mapped("invoice_line_id"))

    def _check_declaration_lines(self, lines, fr_qty, pt_qty):
        for line in lines:
            if line.src_dest_country_id == self.env.ref("base.fr"):
                self.assertEquals(line.suppl_unit_qty, fr_qty)
            if line.src_dest_country_id == self.env.ref("base.pt"):
                self.assertEquals(line.suppl_unit_qty, pt_qty)

    def _create_declaration(self, dec_type):
        report = self.env["l10n.es.intrastat.product.declaration"].create(
            {
                "year": datetime.today().year,
                "month": str(datetime.today().month).zfill(2),
                "type": dec_type,
                "action": "replace",
            }
        )
        report.action_gather()
        return report

    def test_report_creation_dispatches(self):
        # Generate report
        report_dispatches = self._create_declaration("dispatches")
        self._check_move_lines_present(
            self.invoices["dispatches"]["invoices"],
            report_dispatches.computation_line_ids,
        )
        report_dispatches.generate_declaration()
        self.assertEquals(
            len(report_dispatches.declaration_line_ids), 2
        )  # One line for each country
        self.assertEquals(
            report_dispatches.declaration_line_ids.mapped("hs_code_id"),
            self.env["hs.code"].browse(1),
        )
        self._check_declaration_lines(
            report_dispatches.declaration_line_ids,
            self.invoices["dispatches"][self.partner_1.country_id],
            self.invoices["dispatches"][self.partner_2.country_id],
        )
        csv_result = report_dispatches._generate_csv()
        csv_lines = csv_result.decode("utf-8").rstrip().splitlines()
        self.assertEquals(len(csv_lines), 2)
        for line in csv_lines:
            items = line.split(";")
            self.assertTrue(items[0] in ("PT", "FR"))
            self.assertEquals(items[6], self.env["hs.code"].browse(1).local_code)

    def test_report_creation_dispatches_notes(self):
        self.product.origin_country_id = False
        report_dispatches = self._create_declaration("dispatches")
        invoice_0 = self.invoices["dispatches"]["invoices"][0]
        vat_note = _("Missing partner vat on invoice %s.") % invoice_0.name
        self.assertTrue(vat_note in report_dispatches.note)
        origin_note = (
            _("Missing origin country on product %s.") % self.product.name_get()[0][1]
        )
        self.assertTrue(origin_note in report_dispatches.note)

    def test_report_creation_arrivals(self):
        # Generate report
        report_arrivals = self._create_declaration("arrivals")
        self._check_move_lines_present(
            self.invoices["arrivals"]["invoices"], report_arrivals.computation_line_ids
        )
        report_arrivals.generate_declaration()
        self.assertEquals(
            len(report_arrivals.declaration_line_ids), 2
        )  # One line for each country
        self.assertEquals(
            report_arrivals.declaration_line_ids.mapped("hs_code_id"),
            self.env["hs.code"].browse(1),
        )
        self._check_declaration_lines(
            report_arrivals.declaration_line_ids,
            self.invoices["arrivals"][self.partner_1.country_id],
            self.invoices["arrivals"][self.partner_2.country_id],
        )
        csv_result = report_arrivals._generate_csv()
        csv_lines = csv_result.decode("utf-8").rstrip().splitlines()
        self.assertEquals(len(csv_lines), 2)
        for line in csv_lines:
            items = line.split(";")
            self.assertTrue(items[0] in ("PT", "FR"))
            self.assertEquals(items[6], self.env["hs.code"].browse(1).local_code)
