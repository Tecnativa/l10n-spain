# Copyright 2023 Binhex - Nicolás Ramos
# Copyright 2024 Binhex - Christian Ramos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
import base64
import os
import subprocess
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.tools.misc import file_path


class L10nEsAtcMod420Report(models.Model):
    _inherit = "l10n.es.aeat.report.tax.mapping"
    _name = "l10n.es.atc.mod420.report"
    _description = "ATC 420 Report"
    _aeat_number = "420"
    _period_quarterly = True
    _period_monthly = False
    _period_yearly = False

    def _default_counterpart_420(self):
        return self.env["account.account"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("code", "like", "4757%"),
            ]
        )[:1]

    company_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        related="company_id.partner_id",
        store=True,
    )
    total_devengado = fields.Float(
        string="[25] Total accrued installments",
        readonly=True,
        compute_sudo=True,
        compute="_compute_total_devengado",
        store=True,
    )

    # Cuotas devueltas en regimen de viajeros
    casilla_23 = fields.Float(
        string="[23] Traveler Base",
        default=0,
        help="Basis of the fee in the passenger regime made by the subject " "passive",
    )
    casilla_24 = fields.Float(
        string="[24] Traveler Fees",
        default=0,
        help="Fee in the passenger regime made by the taxpayer",
    )
    casilla_36 = fields.Float(
        string="[36] Livestock and fishing quotas",
        default=0,
        help="Quota of taxpayers covered by the special regime of the "
        "agriculture, Livestock and fishing",
    )
    casilla_37 = fields.Float(
        string="[37] Quotas Investment goods",
        default=0,
        help="Quota with positive or negative sign, of the regularization of the "
        "quotas supported by the acquisition or import of goods of "
        "investment",
    )
    casilla_38 = fields.Float(
        string="[38] Fee Before activity start",
        default=0,
        help="Quotas supported by the acquisition or importation of goods or "
        "services before the start of business activities or "
        "professionals",
    )
    casilla_39 = fields.Float(
        string="[39] Pro rata fee",
        default=0,
        help="Quotas for application of the final percentage of pro rata",
    )
    total_deducir = fields.Float(
        string="[40] Total deductible installments",
        readonly=True,
        compute_sudo=True,
        compute="_compute_total_deducir",
        store=True,
    )
    diferencia = fields.Float(
        string="[41] Difference",
        readonly=True,
        compute="_compute_diferencia",
        store=True,
        help="Difference between the amounts of boxes 25-40, either its "
        "import positive or negative",
    )
    regularizacion_cuotas = fields.Float(
        string="[42] Regularization of quotas",
        default=0,
        help="Amount corresponding to the quotas supported that could not "
        "be deducted and from which it is a debtor to the Treasury "
        "Public",
    )
    cuotas_compensar = fields.Float(
        string="[43] quotas to compensate",
        default=0,
        help="The installments in favor of the taxpayer from previous periods "
        "pending compensation ",
    )
    a_deducir = fields.Float(
        string="[44] To deduct",
        default=0,
        help="This box will only be completed in the event of "
        "complementary self-assessment",
    )

    resultado_autoliquidacion = fields.Float(
        string="[45] Self-assessment result",
        readonly=True,
        compute="_compute_resultado_autoliquidacion",
        store=True,
    )
    result_type = fields.Selection(
        selection=[
            ("I", _("To enter")),
            ("D", _("To return")),
            ("C", _("To compensate")),
            ("N", _("No activity/Zero result")),
        ],
        string="Result type",
        compute="_compute_result_type",
    )
    output_type = fields.Selection(
        selection=[
            ("B", "Print Draft"),
            ("I", "Print autoliquidation final"),
            ("T", "Telematic"),
        ],
        string="Output type",
        default="T",
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bank account",
    )
    counterpart_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Counterpart account",
        default=_default_counterpart_420,
    )
    allow_posting = fields.Boolean(string="Allow posting", default=True)

    @api.depends("tax_line_ids", "tax_line_ids.amount", "casilla_23", "casilla_24")
    def _compute_total_devengado(self):
        casillas_devengado = (3, 6, 9, 12, 15, 18, 20, 22)
        for report in self:
            tax_lines = report.tax_line_ids.filtered(
                lambda x: x.field_number in casillas_devengado
            )
            report.total_devengado = sum(tax_lines.mapped("amount"))
            if not float_is_zero(report.casilla_23, precision_digits=2):
                report.total_devengado -= report.casilla_24

    @api.depends("tax_line_ids", "tax_line_ids.amount")
    def _compute_total_deducir(self):
        casillas_deducir = (27, 29, 31, 33, 35, 36, 37, 38, 39)
        for report in self:
            tax_lines = report.tax_line_ids.filtered(
                lambda x: x.field_number in casillas_deducir
            )
            report.total_deducir = sum(tax_lines.mapped("amount"))

    @api.depends("total_devengado", "total_deducir")
    def _compute_diferencia(self):
        for report in self:
            report.diferencia = report.total_devengado - report.total_deducir

    @api.depends("total_devengado")
    def _compute_resultado_autoliquidacion(self):
        for report in self:
            report.resultado_autoliquidacion = (
                report.diferencia
                + report.regularizacion_cuotas
                - report.cuotas_compensar
                - report.a_deducir
            )

    def _compute_allow_posting(self):
        self.allow_posting = True

    @api.depends("resultado_autoliquidacion", "period_type")
    def _compute_result_type(self):
        for report in self:
            if report.resultado_autoliquidacion == 0:
                report.result_type = "N"
            elif report.resultado_autoliquidacion > 0:
                report.result_type = "I"
            else:
                if report.period_type in ("4T", "12"):
                    report.result_type = "D"
                else:
                    report.result_type = "C"

    def button_confirm(self):
        """Check records"""
        msg = ""
        for mod420 in self:
            if mod420.result_type == "I" and not mod420.bank_account_id:
                msg = _("Select an account for making the charge")
            if mod420.result_type == "D" and not mod420.bank_account_id:
                msg = _("Select an account for receiving the money")
        if msg:
            # Don't raise error, because data is not used
            # raise exceptions.Warning(msg)
            pass
        return super().button_confirm()

    @api.model
    def _prepare_counterpart_move_line(self, account, debit, credit):
        vals = super()._prepare_counterpart_move_line(account, debit, credit)
        vals.update(
            {
                "partner_id": self.env.ref("l10n_es_atc.res_partner_atc").id,
            }
        )
        return vals

    def button_modelo_sobre(self):
        self.ensure_one()
        url = "/l10n_es_atc_mod420/static/src/pdf/caratula_sobre_420.pdf"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
            "tag": "reload",
        }

    def _make_cmd(self, dir_paths):
        JAVA_BIN = "java -cp"
        JAR_PATH = file_path("l10n_es_atc_mod420/static/jar/pa-mod420-9.2.0.jar")
        MAIN_CLASS = "org.grecasa.ext.pa.mod420.MIModelo420"
        xml_path = dir_paths["xml_path"]
        errores_path = dir_paths["errores_path"]
        control_path = dir_paths["control_path"]
        resultado_path = dir_paths["resultado_path"]
        servicio_path = dir_paths["servicio_path"]
        cmd = [
            JAVA_BIN,
            JAR_PATH,
            MAIN_CLASS,
            f'/E:"{xml_path}"',
            f'/R:"{errores_path}"',
            f'/F:"{control_path}"',
            f'/S:"{self.output_type}"',
            f'/T:"{resultado_path}"',
            '/P:"Mod420"',
            '/N:"N"',
            f'/W:"{servicio_path}"',
        ]
        return cmd

    def _make_tmp_dir(self):
        TMP_DIR = tempfile.mkdtemp()
        xml_path = os.path.join(TMP_DIR, "M420.xml")
        errores_path = os.path.join(TMP_DIR, "FICH_ERRORES.txt")
        control_path = os.path.join(TMP_DIR, "FICH_CONTROL.txt")
        resultado_path = os.path.join(TMP_DIR, "Resultado")
        servicio_path = os.path.join(TMP_DIR, "Servicio420")
        os.makedirs(resultado_path, exist_ok=True)
        os.makedirs(servicio_path, exist_ok=True)
        return {
            "xml_path": xml_path,
            "errores_path": errores_path,
            "control_path": control_path,
            "resultado_path": resultado_path,
            "servicio_path": servicio_path,
        }

    def action_generar_mod420(self):
        self.ensure_one()
        report_name = "l10n_es_atc_mod420.mod420_report_xml"
        xml_data = self.env["ir.actions.report"]._render_qweb_xml(
            report_name, self.ids
        )[0]
        generated_filename = "Mod420.dec" if self.output_type == "T" else "Mod420.pdf"
        dir_paths = self._make_tmp_dir()
        with open(dir_paths["xml_path"], "w", encoding="iso-8859-1") as f:
            f.write(xml_data.decode("iso-8859-1"))
        cmd = self._make_cmd(dir_paths)
        try:
            result = subprocess.run(
                " ".join(cmd), shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                raise UserError(
                    f"Error al generar el modelo 420:\n"
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
            with open(dir_paths["errores_path"], encoding="iso-8859-1") as f:
                errores = f.read()
            if errores:
                raise UserError(
                    _(
                        "No se pudo generar el archivo. Errores encontrados:\n %s",
                        errores,
                    )
                )
        # Verificar PDF
        resultado_path = dir_paths["resultado_path"]
        pdf_path = os.path.join(resultado_path, "mod420.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = next(
                (
                    os.path.join(resultado_path, f)
                    for f in os.listdir(resultado_path)
                    if f.startswith(generated_filename)
                ),
                None,
            )
            if not pdf_path or not os.path.exists(pdf_path):
                raise UserError(
                    _(
                        "Declaracion no generada. Revisa si el XML es válido y "
                        "los parámetros correctos."
                    )
                )
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        attachment = self.env["ir.attachment"].search(
            [
                ("name", "=", generated_filename),
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(
                {
                    "datas": base64.b64encode(pdf_content).decode("ascii"),
                    "mimetype": "application/pdf",
                }
            )
        else:
            attachment = self.env["ir.attachment"].create(
                {
                    "name": generated_filename,
                    "type": "binary",
                    "datas": base64.b64encode(pdf_content).decode("ascii"),
                    "res_model": self._name,
                    "res_id": self.id,
                    "mimetype": "application/pdf",
                }
            )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
        }

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
