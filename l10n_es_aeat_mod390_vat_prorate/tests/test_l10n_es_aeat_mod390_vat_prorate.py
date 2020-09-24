# Copyright 2020 Tecnativa - Víctor Martínez
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0

from odoo.addons.l10n_es_aeat_mod390.tests.test_l10n_es_aeat_mod390 \
    import TestL10nEsAeatMod390Base

import logging
from odoo import exceptions
_logger = logging.getLogger(__name__)


class TestL10nEsAeatMod390VatProrateBase(TestL10nEsAeatMod390Base):
    def setUp(self):
        super().setUp()
        self.taxes_sale = {
            # tax code: (base, tax_amount)
            'S_IVA21B': (1400, 294),
            'S_IVA21B//neg': (-140, -29.4),
            'S_IVA0': (200, 0),
        }
        self.taxes_purchase = {
            # tax code: (base, tax_amount)
            'P_IVA4_BC': (240, 9.6),
            'P_IVA10_BC': (250, 25),
            'P_IVA21_BC': (260, 54.6),
        }
        self.invoice_purchase = self._invoice_purchase_create('2017-01-03')
        self.invoice_sale = self._invoice_sale_create('2017-01-13')
        self.journal = self.env['account.journal'].create({
            'name': 'Test journal',
            'code': 'TEST',
            'type': 'general',
        })
        self.account_type = self.env['account.account.type'].create({
            'name': 'Test account type',
            'type': 'other',
        })
        self.counterpart_account = self.env['account.account'].create({
            'name': 'Test counterpart account',
            'code': 'COUNTERPART',
            'user_type_id': self.account_type.id,
        })
        self.model390.write({
            'journal_id': self.journal.id,
        })
        self.model390_with_vat_prorate = self.model390.copy()
        self.model390_with_vat_prorate.write({
            'vat_prorate_type': 'general',
            'vat_prorate_percent': 10
        })


class TestL10nEsAeatMod390VatProrate(TestL10nEsAeatMod390VatProrateBase):
    def test_exceptions(self):
        # Error vat_prorate_percent > 100
        with self.assertRaises(exceptions.ValidationError):
            self.model390_with_vat_prorate.write({
                'vat_prorate_percent': 110
            })
            self.model390_with_vat_prorate.button_calculate()

    def test_vat_prorate(self):
        self.model390_with_vat_prorate.button_calculate()
        lines = self.model390_with_vat_prorate.tax_line_ids
        # check vat_prorate_percent
        self.assertEqual(
            len(self.model390_with_vat_prorate.prorate_ids),
            1
        )
        self.assertAlmostEqual(
            self.model390_with_vat_prorate.vat_prorate_percent,
            10.00,
            2
        )
        # lines amount 0
        lines_amount_0 = [62, 197, 612, 614]
        for line_amount_0 in lines_amount_0:
            self.assertAlmostEqual(
                lines.filtered(
                    lambda x: x.map_line_id.field_number == line_amount_0
                ).amount, 0.00, 2
            )
        # 191
        self.assertAlmostEqual(
            lines.filtered(
                lambda x: x.map_line_id.field_number == 191
            ).amount, 8.64, 2
        )
        # 604
        self.assertAlmostEqual(
            lines.filtered(
                lambda x: x.map_line_id.field_number == 604
            ).amount, 22.5, 2
        )
        # 606
        self.assertAlmostEqual(
            lines.filtered(
                lambda x: x.map_line_id.field_number == 606
            ).amount, 49.14, 2
        )
        # confirm
        self.model390_with_vat_prorate.button_confirm()
        self.assertEqual(self.model390_with_vat_prorate.state, 'done')
