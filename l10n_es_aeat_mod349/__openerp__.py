# -*- coding: utf-8 -*-
# Copyright 2004-2011 - Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2013 - Top Consultant Software Creations S.L.
#                - (http://www.topconsultant.es/)
# Copyright 2014-2015 - Serv. Tecnol. Avanzados
#                     - Pedro M. Baeza (http://www.serviciosbaeza.com)
# Copyright 2016 - Tecnativa - Angel Moya <odoo@tecnativa.com>
# Copyright 2017 - Tecnativa - Luis M. Ontalba <luis.martinez@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Modelo 349 AEAT",
    "version": "9.0.2.0.0",
    "author": "Pexego, "
              "Top Consultant, "
              "Tecnativa,"
              "Eficent,"
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": 'Localisation/Accounting',
    'website': 'https://github.com/OCA/l10n-spain',
    "depends": [
        "account_invoice_refund_link",
        "l10n_es_aeat",
        "l10n_es",
    ],
    'data': [
        "data/aeat_349_map_data.xml",
        "data/aeat_export_mod349_partner_refund_data.xml",
        "data/aeat_export_mod349_partner_data.xml",
        "data/aeat_export_mod349_data.xml",
        "views/account_tax_view.xml",
        "views/aeat_349_map_view.xml",
        "views/mod349_view.xml",
        'report/common_templates.xml',
        "report/aeat_mod349.xml",
        "report/report_views.xml",
        "security/ir.model.access.csv",
        "security/mod_349_security.xml",
    ],
    'installable': True,
}
