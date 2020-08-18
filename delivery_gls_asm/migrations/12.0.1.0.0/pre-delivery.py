# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

renamed_fields_asm = [
    ("delivery.carrier", "delivery_carrier", "asm_userid", "gls_asm_uid"),
    ("delivery.carrier", "delivery_carrier", "asm_service", "gls_asm_service"),
    ("delivery.carrier", "delivery_carrier", "asm_shiptime", "gls_asm_shiptime"),
    (
        "stock.picking",
        "stock_picking",
        "x_carrier_shipping_ref",
        "gls_asm_public_tracking_ref",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    # Now delivery_asm is the OCA module delivery_gls_asm
    openupgrade.rename_fields(env, renamed_fields_asm)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE delivery_carrier SET delivery_type = 'gls_asm'
        WHERE delivery_type = 'asm'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_packaging SET package_carrier_type = 'none'
        WHERE package_carrier_type = 'asm'
        """,
    )
    # We need to adapt rates as well
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE delivery_rate SET type = 'gls_asm'
        WHERE type = 'asm'
        """,
    )
