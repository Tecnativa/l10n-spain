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

    @api.depends("tax_line_ids", "tax_line_ids.amount")
    def _compute_total_devengado(self):
        casillas_devengado = (3, 6, 9, 12, 15, 18, 20, 22, 24)
        for report in self:
            tax_lines = report.tax_line_ids.filtered(
                lambda x: x.field_number in casillas_devengado
            )
            report.total_devengado = sum(tax_lines.mapped("amount"))

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

    def action_generar_borrador_pdf(self):
        self.ensure_one()
        # if not self.xml_data:
        #     raise UserError("No hay XML para generar el PDF.")

        # Configuración de rutas
        SRC_FILES = "/opt/odoo/auto/addons/l10n_es_atc_mod420/static/src/files"
        JAR_PATH = (
            "/opt/odoo/auto/addons/l10n_es_atc_mod420/static/"
            "src/files/pa-mod420-9.2.0.jar"
        )
        MAIN_CLASS = "org.grecasa.ext.pa.mod420.MIModelo420"
        TMP_DIR = tempfile.mkdtemp()
        xml_path = os.path.join(SRC_FILES, "M420-Ingreso.xml")
        errores_path = os.path.join(TMP_DIR, "FICH_ERRORES.txt")
        control_path = os.path.join(TMP_DIR, "FICH_CONTROL.txt")
        resultado_path = os.path.join(TMP_DIR, "Resultado")
        servicio_path = os.path.join(TMP_DIR, "Servicio420")
        os.makedirs(resultado_path, exist_ok=True)
        os.makedirs(servicio_path, exist_ok=True)

        # with open(xml_path, 'w', encoding='iso-8859-1') as f:
        #     f.write(self.xml_data)

        cmd = [
            "java",
            "-cp",
            JAR_PATH,
            MAIN_CLASS,
            f'/E:"{xml_path}"',
            f'/R:"{errores_path}"',
            f'/F:"{control_path}"',
            '/S:"B"',
            f'/T:"{resultado_path}"',
            '/P:"borrador"',
            '/N:"N"',
            f'/W:"{servicio_path}"',
        ]

        try:
            result = subprocess.run(
                " ".join(cmd), shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                raise UserError(
                    f"❌ Error al generar el PDF del borrador:\n"
                    f"🔁 Código de salida: {result.returncode}\n"
                    f"📤 STDOUT:\n{result.stdout}\n"
                    f"📥 STDERR:\n{result.stderr}"
                )
        except Exception as e:
            raise UserError(
                _(f"❌ Excepción durante la ejecución del comando:\n{ustr(e)}")
            ) from e

        # Verificar PDF
        pdf_path = os.path.join(resultado_path, "borrador.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = next(
                (
                    os.path.join(resultado_path, f)
                    for f in os.listdir(resultado_path)
                    if f.startswith("borrador420_")
                ),
                None,
            )
            if not pdf_path or not os.path.exists(pdf_path):
                raise UserError(
                    _(
                        "PDF no generado. Revisa si el XML es válido y "
                        "los parámetros correctos."
                    )
                )

        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

        self.env["ir.attachment"].create(
            {
                "name": "Borrador Modelo 420",
                "type": "binary",
                "datas": base64.b64encode(pdf_content).decode("ascii"),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            }
        )
