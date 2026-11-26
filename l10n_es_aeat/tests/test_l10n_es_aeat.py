# Copyright 2016-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import exceptions

from odoo.addons.base.tests.common import BaseCommon


class TestL10nEsAeat(BaseCommon):
    _test_user_groups = (
        "base.group_user",
        "base.group_system",
        "account.group_account_manager",
    )

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.export_model = cls.env["l10n.es.aeat.report.export_to_boe"]
        cls.partner = cls.env["res.partner"].create({"name": "test partner"})

    def test_format_string(self) -> None:
        text = " &'(),-./01:;abAB_ÇÑ\"áéíóúÁÉÍÓÚ+!"
        self.assertEqual(
            self.export_model._format_string(text, len(text)),
            " &'(),-./01:;ABAB_ÇÑAEIOUAEIOU   ".encode("iso-8859-1"),
        )

    def test_parse_vat_info_additional_identifiers(self) -> None:
        """Without a useful VAT, the first additional identifier gives the
        identifier type; a valid Spanish or intra-community VAT goes first."""
        es, pt, it, us = (
            self.env.ref(f"base.{code}").id for code in ("es", "pt", "it", "us")
        )
        cases = [
            ({"country_id": pt, "l10n_es_passport": "P"}, ("PT", "03", "P")),
            ({"country_id": pt, "l10n_es_foreign_id": "F"}, ("PT", "04", "F")),
            ({"country_id": pt, "l10n_es_res_cert": "R"}, ("PT", "05", "R")),
            ({"country_id": pt, "l10n_es_other_id": "O"}, ("PT", "06", "O")),
            (
                {"country_id": pt, "l10n_es_passport": "P", "l10n_es_other_id": "O"},
                ("PT", "03", "P"),
            ),
            (
                {"country_id": us, "vat": "NO_DISPONIBLE", "l10n_es_res_cert": "R"},
                ("US", "05", "R"),
            ),
            (
                {"country_id": es, "vat": "12345678Z", "l10n_es_passport": "P"},
                ("ES", "", "12345678Z"),
            ),
            (
                {"country_id": es, "vat": "INVALID-NIF", "l10n_es_passport": "P"},
                ("ES", "03", "P"),
            ),
            (
                {"country_id": pt, "vat": "FR61954506077", "l10n_es_passport": "P"},
                ("FR", "02", "61954506077"),
            ),
            ({"country_id": es}, ("ES", "", "")),
            ({"country_id": es, "vat": "ESINVALID-NIF"}, ("ES", "", "INVALIDNIF")),
            (
                {"country_id": it, "vat": "ITMRTMTT91D08F205J"},
                ("IT", "04", "MRTMTT91D08F205J"),
            ),
        ]
        Partner = self.env["res.partner"].with_context(no_vat_validation=True)
        for vals, expected in cases:
            with self.subTest(vals=vals):
                partner = Partner.create({"name": "Test partner", **vals})
                self.assertEqual(partner._parse_aeat_vat_info(), expected)

    def test_parse_vat_info_es_wo_prefix(self) -> None:
        self.partner.write(
            {"vat": "12345678Z", "country_id": self.env.ref("base.es").id}
        )
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "ES")
        self.assertEqual(identifier_type, "")
        self.assertEqual(vat_number, "12345678Z")

    def test_parse_vat_info_es_w_prefix(self) -> None:
        self.partner.vat = "ES12345678Z"
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "ES")
        self.assertEqual(identifier_type, "")
        self.assertEqual(vat_number, "12345678Z")

    def test_parse_vat_info_es_passport_exception(self) -> None:
        with self.assertRaises(exceptions.ValidationError):
            self.partner.write(
                {"vat": "ZZ_MY_PASSPORT", "country_id": self.env.ref("base.es").id}
            )

    def test_parse_vat_info_fr_wo_prefix(self) -> None:
        self.partner.write(
            {"vat": "61954506077", "country_id": self.env.ref("base.fr").id}
        )
        country_code, _identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "FR")
        self.assertEqual(vat_number, "61954506077")

    def test_parse_vat_info_fr_w_prefix(self) -> None:
        self.partner.vat = "fr61954506077"
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "FR")
        self.assertEqual(identifier_type, "02")
        self.assertEqual(vat_number, "61954506077")

    def test_parse_vat_info_it_valid_vat(self) -> None:
        self.partner.write(
            {"vat": "12345670017", "country_id": self.env.ref("base.it").id}
        )
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "IT")
        self.assertEqual(identifier_type, "02")
        self.assertEqual(vat_number, "12345670017")

    def test_parse_vat_info_it_codice_fiscale(self) -> None:
        """A personal "codice fiscale" is not a "partita IVA": sending it to
        the SII as identifier type 02 (NIF-IVA) gets rejected with error
        1104 "Valor del campo ID incorrecto".
        """
        # base_vat doesn't accept a "codice fiscale" as VAT anymore
        self.partner.with_context(no_vat_validation=True).write(
            {"vat": "MRTMTT91D08F205J", "country_id": self.env.ref("base.it").id}
        )
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "IT")
        self.assertEqual(identifier_type, "04")
        self.assertEqual(vat_number, "MRTMTT91D08F205J")

    def test_parse_vat_info_gf_wo_prefix(self) -> None:
        self.partner.write(
            {"vat": "61954506077", "country_id": self.env.ref("base.gf").id}
        )
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "FR")
        self.assertEqual(identifier_type, "04")
        self.assertEqual(vat_number, "61954506077")

    def test_parse_vat_info_gf_w_prefix(self) -> None:
        self.partner.vat = "GF61954506077"
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "FR")
        self.assertEqual(identifier_type, "04")
        self.assertEqual(vat_number, "GF61954506077")

    def test_parse_vat_info_cu_wo_prefix(self) -> None:
        self.partner.write(
            {"vat": "12345678Z", "country_id": self.env.ref("base.cu").id}
        )
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "CU")
        self.assertEqual(identifier_type, "04")
        self.assertEqual(vat_number, "12345678Z")

    def test_parse_vat_info_cu_w_prefix(self) -> None:
        self.partner.vat = "CU12345678Z"
        country_code, identifier_type, vat_number = self.partner._parse_aeat_vat_info()
        self.assertEqual(country_code, "CU")
        self.assertEqual(identifier_type, "04")
        self.assertEqual(vat_number, "CU12345678Z")

    def test_parse_vat_info_no_collision_between_partners(self) -> None:
        """Two partners without VAT and the same country must not share their
        AEAT identification. This guards against a caching regression where the
        result was keyed only on (vat, country_id), so partners without VAT in
        the same country returned another partner's additional identifier.
        """
        portugal = self.env.ref("base.pt")
        partner_a = self.env["res.partner"].create(
            {
                "name": "PT partner A",
                "country_id": portugal.id,
                "l10n_es_other_id": "PT_IDENTIFICATION_A",
            }
        )
        partner_b = self.env["res.partner"].create(
            {
                "name": "PT partner B",
                "country_id": portugal.id,
                "l10n_es_other_id": "PT_IDENTIFICATION_B",
            }
        )
        self.assertEqual(
            partner_a._parse_aeat_vat_info(),
            ("PT", "06", "PT_IDENTIFICATION_A"),
        )
        self.assertEqual(
            partner_b._parse_aeat_vat_info(),
            ("PT", "06", "PT_IDENTIFICATION_B"),
        )

    def test_unique_date_range(self) -> None:
        self.env["l10n.es.aeat.map.tax"].create(
            {"date_from": "2020-01-01", "date_to": "2020-12-31", "model": 303}
        )
        with self.assertRaises(exceptions.UserError):
            self.env["l10n.es.aeat.map.tax"].create(
                {"date_to": "2021-01-01", "model": 303}
            )

    def test_tax_map_cache_is_invalidated_after_tax_create_and_delete(self) -> None:
        company = self.env.company
        tax_template_xmlid = "account_tax_template_aeat_cache_test"
        self.assertFalse(company._get_tax_id_from_xmlid(tax_template_xmlid))

        tax = self.env["account.tax"].create(
            {
                "name": "AEAT cache invalidation test",
                "amount_type": "percent",
                "amount": 21,
                "type_tax_use": "sale",
                "company_id": company.id,
            }
        )
        external_id = self.env["ir.model.data"].create(
            {
                "module": "account",
                "name": f"{company.id}_{tax_template_xmlid}",
                "model": "account.tax",
                "res_id": tax.id,
                "noupdate": True,
            }
        )
        self.assertEqual(company._get_tax_id_from_xmlid(tax_template_xmlid), tax.id)

        external_id.unlink()
        tax.unlink()
        self.assertFalse(company._get_tax_id_from_xmlid(tax_template_xmlid))

    def test_map_aeat_iso_code_greece(self) -> None:
        res_partner_obj = self.env["res.partner"]
        greece_country = self.env.ref("base.gr")
        iso_code = "EL"
        mapping_return = res_partner_obj._map_aeat_country_iso_code(greece_country)
        self.assertEqual(iso_code, mapping_return)

    def test_map_aeat_iso_code_no_mapping(self) -> None:
        res_partner_obj = self.env["res.partner"]
        spain_country = self.env.ref("base.es")
        iso_code = "ES"
        mapping_return = res_partner_obj._map_aeat_country_iso_code(spain_country)
        self.assertEqual(iso_code, mapping_return)

    def test_has_valid_aeat_identification(self) -> None:
        partner_with_vat = self.env["res.partner"].create(
            {
                "name": "Partner with VAT",
                "vat": "ES12345678Z",
            }
        )
        self.assertTrue(partner_with_vat._has_valid_aeat_identification())
        for field_name in (
            "l10n_es_passport",
            "l10n_es_foreign_id",
            "l10n_es_res_cert",
            "l10n_es_other_id",
        ):
            partner_with_additional_identifier = self.env["res.partner"].create(
                {
                    "name": f"Partner with {field_name}",
                    "country_id": self.env.ref("base.pt").id,
                    field_name: "ABC123456",
                }
            )
            self.assertTrue(
                partner_with_additional_identifier._has_valid_aeat_identification()
            )
            self.assertFalse(
                partner_with_additional_identifier._has_valid_aeat_identification(
                    allow_alternative_identification=False
                )
            )
        partner_without_identification = self.env["res.partner"].create(
            {
                "name": "Partner without identification",
                "country_id": self.env.ref("base.es").id,
            }
        )
        self.assertFalse(
            partner_without_identification._has_valid_aeat_identification()
        )
        partner_without_identification.country_id = self.env.ref("base.us")
        self.assertFalse(
            partner_without_identification._has_valid_aeat_identification()
        )
        partner_only_identifier = self.env["res.partner"].create(
            {
                "name": "Partner with unavailable identifier",
                "country_id": self.env.ref("base.us").id,
                "l10n_es_other_id": "NO_DISPONIBLE",
            }
        )
        self.assertFalse(partner_only_identifier._has_valid_aeat_identification())
        partner_with_blank_identifier = self.env["res.partner"].create(
            {
                "name": "Partner with blank identifier",
                "country_id": self.env.ref("base.us").id,
                "l10n_es_other_id": "   ",
            }
        )
        self.assertFalse(partner_with_blank_identifier._has_valid_aeat_identification())
        partner_without_useful_vat = (
            self.env["res.partner"]
            .with_context(no_vat_validation=True)
            .create(
                {
                    "name": "Partner with unavailable VAT",
                    "vat": "NO_DISPONIBLE",
                }
            )
        )
        self.assertFalse(partner_without_useful_vat._has_valid_aeat_identification())
        partner_with_vat_and_identifier = self.env["res.partner"].create(
            {
                "name": "Partner with VAT and alternative identifier",
                "vat": "ES12345678Z",
                "l10n_es_other_id": "ABC123456",
            }
        )
        self.assertTrue(
            partner_with_vat_and_identifier._has_valid_aeat_identification(
                allow_alternative_identification=False
            )
        )
        self.assertFalse(
            partner_only_identifier._has_valid_aeat_identification(
                allow_alternative_identification=False
            )
        )
