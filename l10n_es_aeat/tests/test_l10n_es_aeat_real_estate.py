# Copyright 2025 Netkia - Carlos Sainz-Pardo
# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.exceptions import ValidationError
from odoo.fields import Command

from .common import TestL10nEsAeatModBase

_logger = logging.getLogger("aeat")


class TestL10nEsAeatRealEstate(TestL10nEsAeatModBase):
    # Set 'debug' attribute to True to easy debug this test
    # Do not forget to include '--log-handler aeat:DEBUG' in Odoo command line
    debug = False

    # Referencias catastrales generadas aleatoriamente
    references = {  # noqa: RUF012
        1: "8374992BV4192Q4560EG",
        2: "7466896WH0452Y6611MK",
        3: "5910144GZ3516I1918GW",
        4: "0982928DM2611S1798DJ",
    }

    def _base_vals(self, name="Test RE"):
        return {
            "name": name,
            "partner_id": self.supplier.id,
            "address_type": "CALLE",
            "address": "C/ Prueba",
            "number_type": "NUM",
            "number": 5,
            "city": "Madrid",
            "zip": "28001",
        }

    def test_01_foreign_estate_without_state(self) -> None:
        estate = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals(),
                "country_id": self.env.ref("base.pt").id,
                "zip": "1000-001",
            }
        )
        self.assertTrue(estate.check_ok)
        self.assertEqual(estate.zip, "1000-001")

    def test_compute_real_estate_situation(self):
        # Caso 1: Sin referencia → situación 4
        r1 = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 1"),
                "city": "Torrelavega",
                "zip": "39301",
                "state_id": self.env.ref("base.state_es_s").id,  # Cantabria
                "reference": False,
            }
        )
        self.assertEqual(r1.real_estate_situation, "4")

        # Caso 2: Con referencia y código fuera del PV/NA → situación 1
        r2 = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 2"),
                "reference": self.references[1],
                "state_id": self.env.ref("base.state_es_m").id,  # Madrid
            }
        )
        self.assertEqual(r2.real_estate_situation, "1")

        # Caso 3a: Vizcaya (BI) → situación 2
        r3 = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 3"),
                "city": "Bilbao",
                "zip": "48001",
                "reference": self.references[2],
                "state_id": self.env.ref("base.state_es_bi").id,
            }
        )
        self.assertEqual(r3.real_estate_situation, "2")

        # Caso 3b: Guipúzcoa (SS) → situación 2
        r3b = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 3b"),
                "city": "San Sebastián",
                "zip": "20001",
                "reference": self.references[2],
                "state_id": self.env.ref("base.state_es_ss").id,
            }
        )
        self.assertEqual(r3b.real_estate_situation, "2")

        # Caso 3c: Álava (VI) → situación 2
        r3c = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 3c"),
                "city": "Vitoria",
                "zip": "01001",
                "reference": self.references[2],
                "state_id": self.env.ref("base.state_es_vi").id,
            }
        )
        self.assertEqual(r3c.real_estate_situation, "2")

        # Caso 4: Navarra (NA) → situación 3
        r4 = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 4"),
                "city": "Pamplona",
                "zip": "31001",
                "reference": self.references[3],
                "state_id": self.env.ref("base.state_es_na").id,
            }
        )
        self.assertEqual(r4.real_estate_situation, "3")

        # Caso 5: Con referencia pero sin state_id → situación 1
        r5 = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Inmueble 5"),
                "reference": self.references[1],
            }
        )
        self.assertEqual(r5.real_estate_situation, "1")

    def test_normalize_reference(self):
        model = self.env["l10n.es.aeat.real_estate"]
        self.assertEqual(
            model._normalize_reference("8374992BV4192Q-4560EG"),
            "8374992BV4192Q4560EG",
        )
        self.assertEqual(
            model._normalize_reference("8374 992B V4192Q.4560_EG"),
            "8374992BV4192Q4560EG",
        )
        self.assertEqual(model._normalize_reference("abc"), "ABC")
        self.assertEqual(model._normalize_reference(""), "")
        self.assertEqual(model._normalize_reference(None), "")

    def test_is_valid_reference(self):
        model = self.env["l10n.es.aeat.real_estate"]

        # Referencias válidas
        for ref in self.references.values():
            self.assertTrue(model._is_valid_reference(ref), f"{ref} debería ser válida")

        # Casos inválidos
        self.assertFalse(model._is_valid_reference(None))
        self.assertFalse(model._is_valid_reference(""))
        self.assertFalse(
            model._is_valid_reference("1234567AB1234A0001WL")
        )  # control erróneo
        self.assertFalse(model._is_valid_reference("SHORT"))  # demasiado corta
        self.assertFalse(
            model._is_valid_reference("1234567AB1234A0001OJ!")
        )  # demasiado larga
        self.assertFalse(
            model._is_valid_reference("1234567ab1234a0001oj")
        )  # minúsculas

    def test_check_reference_constraint(self):
        # Referencia válida: no lanza excepción
        rec = self.env["l10n.es.aeat.real_estate"].create(
            {**self._base_vals(), "reference": self.references[1]}
        )
        self.assertEqual(rec.reference, self.references[1])

        # Referencia vacía: permitida
        rec_no_ref = self.env["l10n.es.aeat.real_estate"].create(
            {**self._base_vals("Sin ref"), "reference": False}
        )
        self.assertFalse(rec_no_ref.reference)

        # Referencia con separadores: se normaliza y valida correctamente
        ref_with_sep = self.references[1][:7] + "-" + self.references[1][7:]
        rec_sep = self.env["l10n.es.aeat.real_estate"].create(
            {**self._base_vals("Con sep"), "reference": ref_with_sep}
        )
        self.assertTrue(rec_sep.reference)

        # Referencia inválida: lanza ValidationError
        with self.assertRaises(ValidationError):
            self.env["l10n.es.aeat.real_estate"].create(
                {**self._base_vals("Inválida"), "reference": "1234567AB1234A0001WL"}
            )

    def test_compute_check_ok(self):
        # Sin state_id → check_ok=False
        rec_no_state = self.env["l10n.es.aeat.real_estate"].create(
            self._base_vals("Sin estado")
        )
        self.assertFalse(rec_no_state.check_ok)
        self.assertTrue(rec_no_state.error_text)

        # Con state_id → check_ok=True
        rec_with_state = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Con estado"),
                "state_id": self.env.ref("base.state_es_m").id,
            }
        )
        self.assertTrue(rec_with_state.check_ok)
        self.assertFalse(rec_with_state.error_text)

    def test_compute_representative_vat(self):
        partner = self.env["res.partner"].create(
            {"name": "Test VAT partner", "vat": "ES00000000T"}
        )
        rec = self.env["l10n.es.aeat.real_estate"].create(
            {**self._base_vals(), "partner_id": partner.id}
        )
        self.assertEqual(rec.representative_vat, "ES00000000T")

        # Al cambiar el NIF del partner se recalcula
        partner.vat = "ES00000001R"
        self.assertEqual(rec.representative_vat, "ES00000001R")

    def test_01_invoice_report_queries_and_groups_by_real_estate(self):
        real_estate = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals("Invoice report estate"),
                "partner_id": self.customer.id,
                "state_id": self.env.ref("base.state_es_m").id,
            }
        )
        invoice = self._invoice_sale_create(
            "2024-02-01",
            {
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Real estate invoice line",
                            "account_id": self.accounts["700000"].id,
                            "price_unit": 1000,
                            "quantity": 1,
                            "l10n_es_aeat_real_estate_id": real_estate.id,
                        }
                    )
                ]
            },
        )
        report = self.env["account.invoice.report"].search(
            [("move_id", "=", invoice.id)]
        )
        self.assertEqual(report.l10n_es_aeat_real_estate_id, real_estate)

    def _check_creation(self, cases, **common_vals):
        """Create a real estate with each set of values, expecting an error for
        the invalid ones."""
        for case_vals, valid in cases:
            vals = {**self._base_vals(), **common_vals, **case_vals}
            with self.subTest(vals=case_vals):
                if valid:
                    self.env["l10n.es.aeat.real_estate"].create(vals)
                else:
                    with self.assertRaises(ValidationError):
                        self.env["l10n.es.aeat.real_estate"].create(vals)

    def test_reference_outside_the_dgc_cadastre(self):
        """The Basque Country, Navarre and the foreign countries have their own
        cadastral references, without the control characters of the DGC."""
        self._check_creation(
            [
                ({"state_id": self.env.ref("base.state_es_na").id}, True),
                ({"state_id": self.env.ref("base.state_es_bi").id}, True),
                ({"country_id": self.env.ref("base.fr").id}, True),
                ({"state_id": self.env.ref("base.state_es_m").id}, False),
            ],
            reference="201001000123400001",
        )

    def test_municipality_code(self):
        """The INE municipality code has 5 digits, the first two of the province
        of the zip, and it is not checked abroad."""
        self._check_creation(
            [
                ({"municipality_code": "28079"}, True),
                ({"municipality_code": "2807"}, False),
                ({"municipality_code": "2807A"}, False),
                ({"municipality_code": "08019"}, False),
                (
                    {
                        "municipality_code": "751",
                        "zip": "75001",
                        "country_id": self.env.ref("base.fr").id,
                    },
                    True,
                ),
            ]
        )

    def test_aeat_location(self):
        """The models 180 and 347 give the locality only when it is not the
        municipality, and the province as the numeric code of the INE."""
        estate = self.env["l10n.es.aeat.real_estate"].create(
            {
                **self._base_vals(),
                "state_id": self.env.ref("base.state_es_m").id,
                "municipality_code": "28079",
            }
        )
        self.assertEqual(
            estate._get_aeat_location(),
            {
                "locality": "",
                "municipality": "Madrid",
                "municipality_code": "28079",
                "province_code": "28",
                "zip": "28001",
            },
        )
        estate.write({"city": "Aravaca", "zip": "28023", "municipality": "Madrid"})
        location = estate._get_aeat_location()
        self.assertEqual(location["locality"], "Aravaca")
        self.assertEqual(location["municipality"], "Madrid")
        estate.municipality_code = False
        self.assertEqual(estate._get_aeat_location()["province_code"], "28")
        estate.country_id = self.env.ref("base.fr")
        self.assertEqual(estate._get_aeat_location()["province_code"], "")

    def test_sii_347_situation(self):
        """The SII and the model 347 join the Basque Country and Navarre, give 3
        without reference and 4 abroad."""
        foral_reference = "201001000123400001"
        cases = (
            ("base.state_es_m", self.references[1], "1"),
            ("base.state_es_bi", foral_reference, "2"),
            ("base.state_es_na", foral_reference, "2"),
            ("base.state_es_m", False, "3"),
        )
        *estates, abroad = self.env["l10n.es.aeat.real_estate"].create(
            [
                {
                    **self._base_vals(state_xmlid),
                    "state_id": self.env.ref(state_xmlid).id,
                    "reference": reference,
                }
                for state_xmlid, reference, _situation in cases
            ]
            + [
                {
                    **self._base_vals("Abroad"),
                    "country_id": self.env.ref("base.fr").id,
                    "reference": "FR-75056-000AB-0123",
                }
            ]
        )
        self.assertEqual(
            [estate._get_sii_347_situation() for estate in estates + [abroad]],
            [situation for *_values, situation in cases] + ["4"],
        )
        # A situation of the model 180 set by hand is kept
        estate = estates[-1]
        estate.real_estate_situation = "3"
        self.assertEqual(estate._get_sii_347_situation(), "2")
