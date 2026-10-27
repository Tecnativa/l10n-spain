# Copyright 2020-2022 Tecnativa - Pedro M. Baeza
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3).


import openpyxl

from odoo import exceptions, models
from odoo.tools.misc import file_path

UOM_MAPPING = {
    "p/st": "intrastat_unit_pce",
    "100 p/st": "intrastat_unit_100pce",
    "1000 p/st": "intrastat_unit_1000pce",
    "l alc. 100%": "intrastat_unit_l_alc_100_pct",
    "kg 90% sdt": "intrastat_unit_kg_90_pct_sdt",
    "m²": "intrastat_unit_m2",
    "m³": "intrastat_unit_m3",
    "1000 m³": "intrastat_unit_1000m3",
}


class L10nEsPartnerImportWizard(models.TransientModel):
    _name = "l10n.es.intrastat.code.import"
    _description = "Intrastat HS Code Import for Spain"

    def _get_intrastat_unit_id(self, name, unit_ids):
        """Intrastat unit of a name of the file, searched once per name"""
        if name not in unit_ids:
            if name in UOM_MAPPING:
                unit = self.env.ref(f"intrastat_product.{UOM_MAPPING[name]}")
            else:
                unit = self.env["intrastat.unit"].search([("name", "=", name)])
            unit_ids[name] = unit.id
        return unit_ids[name]

    def _import_hs_codes(self):
        code_obj = self.env["hs.code"].with_context(active_test=False)
        path = file_path("l10n_es_intrastat_report/data/Estruc_NC2023.xlsx")
        workbook = openpyxl.load_workbook(path, data_only=True)
        sheet = workbook.worksheets[0]
        rows = []
        parents = []
        prev_level = 0
        for nrow in range(2, sheet.max_row + 1):
            code = (sheet.cell(row=nrow, column=3).value or "").replace(" ", "")
            description = sheet.cell(row=nrow, column=7).value.lstrip("-")
            level = int(sheet.cell(row=nrow, column=4).value)
            temp = prev_level
            while temp > level and parents:
                del parents[-1]
                temp -= 1
            if len(code) < 8 and description != description.upper():
                parents.append(description)
            prev_level = level
            if len(code) != 8:  # bypass parent lines
                continue
            rows.append((nrow, code, " /".join(parents + [description])))
        # One read of the existing codes instead of a search per code
        existing_codes = set(
            code_obj.search_fetch(
                [("local_code", "in", [code for _nrow, code, _desc in rows])],
                ["local_code"],
            ).mapped("local_code")
        )
        unit_ids = {}
        vals_list = []
        for nrow, code, description in rows:
            if code in existing_codes:
                continue
            existing_codes.add(code)
            vals = {"local_code": code, "description": description}
            iu = sheet.cell(row=nrow, column=6).value.replace("\xa0", " ")
            if iu and iu != "-":  # specific unit
                iu_unit_id = self._get_intrastat_unit_id(iu, unit_ids)
                if iu_unit_id:
                    vals["intrastat_unit_id"] = iu_unit_id
                else:
                    raise exceptions.UserError(self.env._("Unit not found: '%s'", iu))
            vals_list.append(vals)
        if vals_list:
            code_obj.create(vals_list)

    def action_import_hs_codes(self):
        company = self.env.company
        if (company.country_id.code or "").lower() != "es":
            raise exceptions.UserError(
                self.env._("Current company is not Spanish, so it can't be configured.")
            )
        self._import_hs_codes()
