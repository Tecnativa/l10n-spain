# Copyright 2025 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import os
import subprocess
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr
from odoo.tools.float_utils import float_is_zero, float_round


class L10nEsAtcReport(models.AbstractModel):
    _name = "l10n.es.atc.report"

    output_type = fields.Selection(
        selection=[
            ("B", "Print Draft"),
            ("I", "Print autoliquidation final"),
            ("T", "Telematic"),
        ],
        string="Output type",
        default="T",
    )
    payment_type = fields.Selection(
        selection=[
            ("1", "1 - Efectivo"),
            ("2", "2 - Adeudo en cuenta"),
            ("3", "3 - Pago fraccionado"),
            ("4", "4 - Domiciliación bancaria"),
            ("5", "5 - Pago telemático"),
            ("6", "6 - Aplazamiento 6 meses medidas Covid"),
        ],
        compute="_compute_payment_type",
        store=True,
        readonly=False,
    )

    @api.depends("output_type")
    def _compute_payment_type(self):
        for record in self:
            if not record.payment_type and record.output_type == "T":
                record.payment_type = "5"

    def _atc_get_messages(self):
        """
        Get the messages to display to the user in case of errors.
        :return: list of messages
        :rtype: list
        """
        messages = []
        partner_company = self.company_id.partner_id
        if not partner_company.street:
            messages.append(_("- The company %s has no street") % partner_company.name)
        if not partner_company.zip:
            messages.append(
                _("- The company %s has no zip code") % partner_company.name
            )
        if not self.payment_type:
            messages.append(_("- Select a payment type"))
        return messages

    def _atc_validate_fields(self):
        """
        Validate the fields to be used in the declaration.
        """
        messages = self._atc_get_messages()
        if messages:
            raise UserError(
                _("Please fix the following errors:\n%s") % "\n".join(messages)
            )

    def _atc_run_cmd(self, report_name, filename, jar_path, main_class):
        """
        Run the command to generate the report
        :param report_name: name of the report to generate
        :param filename: name of the file to generate without extension
        :param jar_path: path to the jar file
        :param main_class: main class
        :return: browse_record(ir.attachment)
        """
        xml_data = self.env["ir.actions.report"]._render_qweb_xml(
            report_name, self.ids
        )[0]
        dir_paths = self._atc_make_tmp_dir(filename)
        with open(dir_paths["xml_path"], "w", encoding="iso-8859-1") as f:
            f.write(xml_data.decode("iso-8859-1"))
        full_filename = (
            f"{filename}.dec" if self.output_type == "T" else f"{filename}.pdf"
        )
        cmd = self._atc_make_cmd(dir_paths, filename, jar_path, main_class)
        try:
            result = subprocess.run(
                " ".join(cmd), shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                raise UserError(
                    f"Error al generar el modelo:\n"
                    f"Código de salida: {result.returncode}\n"
                    f"STDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )
        except Exception as e:
            raise UserError(
                _(f"Excepción durante la ejecución del comando:\n{ustr(e)}")
            ) from e
        # check if there are errors
        if os.path.exists(dir_paths["errores_path"]):
            errores = ""
            with open(dir_paths["errores_path"], encoding="iso-8859-1") as f:
                errores = f.read()
            if errores:
                raise UserError(
                    _(
                        "No se pudo generar el archivo. Errores encontrados:\n %s",
                        errores,
                    )
                )
        file_content = self._atc_get_report_data(dir_paths, full_filename)
        return self._atc_save_report(file_content, full_filename)

    def _atc_make_tmp_dir(self, file_name):
        """
        Create a temporary directory to store the files
        :param file_name: name of the file to create witout extension
        :return: dict with the paths of the files
        :rtype: dict
        """
        TMP_DIR = tempfile.mkdtemp()
        xml_path = os.path.join(TMP_DIR, f"{file_name}.xml")
        errores_path = os.path.join(TMP_DIR, "FICH_ERRORES.txt")
        control_path = os.path.join(TMP_DIR, "FICH_CONTROL.txt")
        resultado_path = os.path.join(TMP_DIR, "Resultado")
        servicio_path = os.path.join(TMP_DIR, "Servicio")
        os.makedirs(resultado_path, exist_ok=True)
        os.makedirs(servicio_path, exist_ok=True)
        return {
            "xml_path": xml_path,
            "errores_path": errores_path,
            "control_path": control_path,
            "resultado_path": resultado_path,
            "servicio_path": servicio_path,
        }

    def _atc_make_cmd(self, dir_paths, filename, jar_path, main_class):
        """
        Make the command to run the java program
        :param dir_paths: dict with the paths of the files
        :param filename: name of the file to generate without extension
        :param jar_path: path to the jar file
        :param main_class: main class the jar file
        :return: list with the command to run
        """
        xml_path = dir_paths["xml_path"]
        errores_path = dir_paths["errores_path"]
        control_path = dir_paths["control_path"]
        resultado_path = dir_paths["resultado_path"]
        servicio_path = dir_paths["servicio_path"]
        cmd = [
            "java -cp",
            jar_path,
            main_class,
            f'/E:"{xml_path}"',
            f'/R:"{errores_path}"',
            f'/F:"{control_path}"',
            f'/S:"{self.output_type}"',
            f'/T:"{resultado_path}"',
            f'/P:"{filename}"',
            '/N:"N"',
            f'/W:"{servicio_path}"',
        ]
        return cmd

    def _atc_get_report_data(self, dir_paths, file_name):
        """
        Get the report data from the file
        :param dir_paths: dict with the paths of the files
        :param file_name: name of the file to get
        :return: content of the file
        :rtype: str
        """
        resultado_path = dir_paths["resultado_path"]
        file_path = os.path.join(resultado_path, file_name)
        if not os.path.exists(file_path):
            raise UserError(
                _(
                    "Declaracion no generada. Revisa si el XML es válido y "
                    "los parámetros correctos."
                )
            )
        file_content = ""
        with open(file_path, "rb") as f:
            file_content = f.read()
        return file_content

    def _atc_save_report(self, file_content, file_name):
        """
        Save the file in the database
        :param file_content: content of the file to save
        :param file_name: name of the file to save
        :return: browse_record(ir.attachment)
        """
        Attachment = self.env["ir.attachment"]
        attachment = Attachment.search(
            [
                ("name", "=", file_name),
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ],
            limit=1,
        )
        datas = base64.b64encode(file_content).decode("ascii")
        if attachment:
            attachment.write({"datas": datas})
        else:
            attachment = Attachment.create(
                {
                    "name": file_name,
                    "type": "binary",
                    "datas": datas,
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
        return attachment

    def _get_amount_by_fields(self, fields):
        report_data = []
        for field_base, field_amount in fields:
            line_vals = self._get_amount_by_field(field_base, field_amount)
            if float_is_zero(line_vals["amount"], precision_digits=2):
                continue
            report_data.append(line_vals)
        return report_data

    def _get_amount_by_field(self, field_base, field_amount):
        """
        Get the amount by field base and field amount
        :param field_base: number of field to calculate the amount
        :param field_amount: number of field to calculate the amount
        :return: dict with base, amount and amount_by_tax
            amount_by_tax is a dict with the tax id as key
            and a dict with base, amount and percentage as value
            {
                tax_id: {
                    "base": base,
                    "amount": amount,
                    "percentage": percentage,
                }
            }
        :rtype: dict
        """
        base_tax_lines = self.tax_line_ids.filtered(
            lambda x: x.field_number == field_base
        )
        tax_lines = self.tax_line_ids.filtered(lambda x: x.field_number == field_amount)
        taxes = tax_lines.mapped("move_line_ids.tax_line_id")
        data_total = {
            "base": 0,
            "amount": 0,
            "amount_by_tax": {},
        }
        for tax in taxes:
            base_map_line = base_tax_lines.map_line_id
            map_line = tax_lines.map_line_id
            base_aml = base_tax_lines.move_line_ids.filtered(
                lambda x, tax=tax: tax in x.tax_ids
            )
            tax_aml = tax_lines.move_line_ids.filtered(
                lambda x, tax=tax: x.tax_line_id == tax
            )
            base = base_map_line.get_amount_from_moves(base_aml)
            amount = map_line.get_amount_from_moves(tax_aml)
            data_total["base"] += base
            data_total["amount"] += amount
            data_total["amount_by_tax"][tax] = {
                "base": self._format_amount(base),
                "amount": self._format_amount(amount),
                "percentage": self._format_amount(tax.amount),
            }
        # format amount
        data_total.update(
            {
                "base": self._format_amount(data_total["amount"]),
                "amount": self._format_amount(data_total["amount"]),
            }
        )
        return data_total

    def _format_amount(self, amount):
        """
        Format amount to 2 decimal places and convert to int
        Example: 1234.56 -> 123456
        """
        return int(float_round(amount * 100, 2))
