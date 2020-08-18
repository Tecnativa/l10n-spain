# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

renamed_fields_seur = [
    ("delivery.carrier", "delivery_carrier", "seur_franchise", "seur_franchise_code"),
    ("delivery.carrier", "delivery_carrier", "seur_ccc", "seur_accounting_code"),
    ("delivery.carrier", "delivery_carrier", "ws_username", "seur_ws_username"),
    ("delivery.carrier", "delivery_carrier", "ws_password", "seur_ws_password"),
    ("delivery.carrier", "delivery_carrier", "seur_cit_username", "seur_userid"),
    ("delivery.carrier", "delivery_carrier", "seur_passwd", "seur_cit_password"),
    ("delivery.carrier", "delivery_carrier", "seur_service_code", "seur_service_code"),
    ("delivery.carrier", "delivery_carrier", "seur_ci", "seur_integration_code"),
    ("delivery.carrier", "delivery_carrier", "seur_cnf_ecbcode", "seur_label_size"),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_packaging SET package_carrier_type = 'none'
        WHERE package_carrier_type = 'seur'
        """,
    )
    # Now delivery_seur is an OCA module developed from scratch
    openupgrade.rename_fields(env, renamed_fields_seur)
    # We remove all the Cash on Delivery code, wich was residual and barely used
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_picking SET x_tipoenvio = 'debido' WHERE x_tipoenvio = 'contra'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner SET x_tipoenvio = 'debido' WHERE x_tipoenvio = 'contra'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE sale_order SET x_tipoenvio = 'debido' WHERE x_tipoenvio = 'contra'
        """,
    )
