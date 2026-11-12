# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestL10nEsIntrastatAeatFile(AccountTestInvoicingCommon):
    """The AEAT file of a declaration built from sales and purchases of goods.

    The expected files are written by hand from the AEAT layout the module
    implements (13 fields, plus the VAT of the counterpart in dispatches, each
    one followed by ';'): any change in them changes what is filed."""

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref(
            "sales_team.group_sale_salesman_all_leads"
        )

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template("es_full")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("base.lang_es").active = True
        cls.company = cls.env.company
        cls.company.write(
            {
                "country_id": cls.env.ref("base.es").id,
                "state_id": cls.env.ref("base.state_es_a").id,
                "vat": "ESA12345674",
                "incoterm_id": cls.env.ref("account.incoterm_FCA").id,
                "intrastat_transport_id": cls.env.ref(
                    "intrastat_product.intrastat_transport_3"
                ).id,
            }
        )
        chart = cls.env["account.chart.template"]
        cls.fp_intra = chart.ref("fp_intra")
        cls.fp_intra_private = chart.ref("fp_intra_private")
        cls.env["l10n.es.intrastat.code.import"].create({}).action_import_hs_codes()
        cls.hs_code = cls.env["hs.code"].search([("local_code", "=", "61091000")])
        cls.product = cls.env["product.product"].create(
            {
                "name": "Cotton T-shirt",
                "type": "consu",
                "weight": 0.25,
                "hs_code_id": cls.hs_code.id,
                "origin_country_id": cls.env.ref("base.pt").id,
            }
        )
        cls.customer_fr = cls.env["res.partner"].create(
            {
                "name": "FR customer",
                "country_id": cls.env.ref("base.fr").id,
                "vat": "FR86792377731",
                "property_account_position_id": cls.fp_intra.id,
            }
        )
        cls.customer_pt = cls.env["res.partner"].create(
            {
                "name": "PT private customer",
                "country_id": cls.env.ref("base.pt").id,
                "property_account_position_id": cls.fp_intra_private.id,
            }
        )
        cls.supplier_de = cls.env["res.partner"].create(
            {
                "name": "DE supplier",
                "country_id": cls.env.ref("base.de").id,
                "vat": "DE123456788",
                "property_account_position_id": cls.fp_intra.id,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        # A second warehouse in Madrid, whose receipts are declared there
        cls.warehouse_madrid = cls.env["stock.warehouse"].create(
            {
                "name": "Madrid",
                "code": "MAD",
                "company_id": cls.company.id,
                "partner_id": cls.env["res.partner"]
                .create(
                    {
                        "name": "Madrid warehouse",
                        "country_id": cls.env.ref("base.es").id,
                        "state_id": cls.env.ref("base.state_es_m").id,
                    }
                )
                .id,
            }
        )

    def _deliver_and_invoice(self, partner, qty, price, warehouse=None):
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = partner
        order_form.warehouse_id = warehouse or self.warehouse
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.product_uom_qty = qty
            line_form.price_unit = price
        order = order_form.save()
        order.action_confirm()
        order.picking_ids.button_validate()
        invoice = order._create_invoices()
        invoice.action_post()
        return invoice

    def _receive_and_bill(self, partner, qty, price):
        order_form = Form(self.env["purchase.order"])
        order_form.partner_id = partner
        order_form.picking_type_id = self.warehouse_madrid.in_type_id
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.product_qty = qty
            line_form.price_unit = price
        order = order_form.save()
        order.button_confirm()
        order.picking_ids.button_validate()
        bill = self.env["account.move"].browse(order.action_create_invoice()["res_id"])
        bill.invoice_date = bill.date = "2025-03-20"
        bill.action_post()
        return bill

    def _refund(self, move):
        """Credit note of the whole invoice from its "Credit Note" button"""
        action = move.action_reverse()
        reversal = Form(
            self.env[action["res_model"]].with_context(
                active_model=move._name, active_ids=move.ids
            )
        ).save()
        refund = self.env["account.move"].browse(reversal.refund_moves()["res_id"])
        refund.action_post()
        return refund

    def _declaration(self, declaration_type):
        declaration = self.env["intrastat.product.declaration"].create(
            {"year": "2025", "month": "03", "declaration_type": declaration_type}
        )
        declaration.action_gather()
        declaration.draft2confirmed()
        return declaration

    def test_chart_fiscal_positions(self):
        """The intra-community positions of the Spanish chart are Intrastat"""
        self.assertEqual(self.fp_intra.intrastat, "b2b")
        self.assertEqual(self.fp_intra_private.intrastat, "b2c")

    @freeze_time("2025-03-20")
    def test_dispatches_file(self):
        self._deliver_and_invoice(self.customer_fr, 100, 12.5)
        self._deliver_and_invoice(self.customer_pt, 2, 15)
        declaration = self._declaration("dispatches")
        self.assertEqual(
            declaration._generate_csv().decode(),
            "FR;03;FCA;11;3;;61091000;PT;;25,00;100;1250,00;1250,00;FR86792377731;\n"
            "PT;03;FCA;12;3;;61091000;PT;;0,50;2;30,00;30,00;QV999999999999;\n",
        )

    @freeze_time("2025-03-20")
    def test_arrivals_file(self):
        """Goods received in the Madrid warehouse are declared in Madrid"""
        self._receive_and_bill(self.supplier_de, 10, 12.345)
        declaration = self._declaration("arrivals")
        action = declaration.confirmed2done()
        expected = "DE;28;FCA;11;3;;61091000;PT;;2,50;10;123,45;123,45;\n"
        self.assertEqual(declaration.xml_attachment_name, "2025-03_arrivals_1.csv")
        self.assertEqual(declaration.xml_attachment_id.raw.content.decode(), expected)
        # The file is downloaded from the declaration
        self.assertIn("field=xml_attachment_datas", action["url"])
        stream = self.env["ir.binary"]._get_stream_from(
            declaration, "xml_attachment_datas"
        )
        self.assertEqual(stream.read().decode(), expected)

    @freeze_time("2025-03-20")
    def test_dispatches_province_of_the_warehouse(self):
        """Goods sent from the Madrid warehouse are declared in Madrid"""
        self._deliver_and_invoice(
            self.customer_fr, 4, 10, warehouse=self.warehouse_madrid
        )
        declaration = self._declaration("dispatches")
        self.assertEqual(
            declaration._generate_csv().decode(),
            "FR;28;FCA;11;3;;61091000;PT;;1,00;4;40,00;40,00;FR86792377731;\n",
        )

    @freeze_time("2025-03-20")
    def test_refunds(self):
        """The credit note of a sale declares the goods coming back as an
        arrival, and the one of a purchase the goods sent back as a dispatch,
        both with a positive value and in the province of the warehouse."""
        self._refund(self._deliver_and_invoice(self.customer_fr, 4, 10))
        self._refund(self._receive_and_bill(self.supplier_de, 2, 20))
        expected = {
            # country, province, CN8, origin, weight, units, value, stat. value
            "arrivals": {
                ("DE", "28", "61091000", "PT", "0,50", "2", "40,00", "40,00"),
                ("FR", "03", "61091000", "PT", "1,00", "4", "40,00", "40,00"),
            },
            "dispatches": {
                ("DE", "28", "61091000", "PT", "0,50", "2", "40,00", "40,00"),
                ("FR", "03", "61091000", "PT", "1,00", "4", "40,00", "40,00"),
            },
        }
        for declaration_type, expected_lines in expected.items():
            csv_lines = (
                self._declaration(declaration_type)
                ._generate_csv()
                .decode()
                .splitlines()
            )
            self.assertEqual(
                {
                    tuple(line.split(";")[i] for i in (0, 1, 6, 7, 9, 10, 11, 12))
                    for line in csv_lines
                },
                expected_lines,
            )

    def test_import_hs_codes_twice(self):
        """Importing the codes again neither duplicates them nor loses their
        supplementary unit"""
        hs_code_model = self.env["hs.code"].with_context(active_test=False)
        count = hs_code_model.search_count([])
        self.env["l10n.es.intrastat.code.import"].create({}).action_import_hs_codes()
        self.assertEqual(hs_code_model.search_count([]), count)
        self.assertEqual(
            self.hs_code.intrastat_unit_id,
            self.env.ref("intrastat_product.intrastat_unit_pce"),
        )
        wine = hs_code_model.search([("local_code", "=", "22042109")])
        self.assertEqual(len(wine), 1)
        self.assertEqual(wine.intrastat_unit_id.name, "l")
