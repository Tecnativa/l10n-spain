# Copyright 2016 Soluntec Proyectos y Soluciones TIC. - Rubén Francés
# Copyright 2016 Soluntec Proyectos y Soluciones TIC. - Nacho Torró
# Copyright 2015 Tecnativa - Pedro M. Baeza
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generate_payment_file(self):
        self.ensure_one()
        if self.payment_method_id.code != "conf_sabadell":
            return super().generate_payment_file()
        # Sabadel payment file
        self._sab_errors()
        txt_file = self._sab_registro_01()
        for line in self.payment_line_ids:
            txt_file += self._sab_registro_02(line)
            txt_file += self._sab_registro_03(line)
            if self.payment_mode_id.conf_sabadell_type == "58":
                txt_file += self._sab_registro_04(line)
        txt_file += self._sab_registro_05()
        return txt_file.encode("ascii"), "%s.xml" % self.name

    def _sab_convert_text(self, text, size, justified="right"):
        text = text if text else ""
        if justified == "left":
            return text[:size].ljust(size)
        else:
            return text[:size].rjust(size)

    def _sab_errors(self):
        # 4 - 43 Nombre ordenante
        if not self.company_partner_bank_id.acc_holder_name:
            raise UserError(
                _("Error: Propietario de la cuenta no establecido para la cuenta %s.")
                % self.company_partner_bank_id.acc_number
            )
        # Errores lineas
        for line in self.payment_line_ids:
            # 19 - 30 Documento identificativo
            if not line.partner_id.vat:
                raise UserError(
                    _("El Proveedor %s no tiene establecido el NIF.")
                    % line.partner_id.name
                )
            # 44 - 110 Domicilio
            if not line.partner_id.street:
                raise UserError(
                    _("El Proveedor %s no tiene establecido el Domicilio.")
                    % line.partner_id.name
                )
            # 111 - 150 Ciudad
            if not line.partner_id.city:
                raise UserError(
                    _("El Proveedor %s no tiene establecida la Ciudad.")
                    % line.partner_id.name
                )
            # 151- 155 CP
            if not line.partner_id.zip:
                raise UserError(
                    _("El Proveedor %s no tiene establecido el C.P.")
                    % line.partner_id.name
                )
            # 253 - 254 Codigo pais
            if not line.partner_id.country_id.code:
                raise UserError(
                    _("El Proveedor %s no tiene establecido el País.")
                    % line.partner_id.name
                )
            # 19 - 29 SWIFT
            if not line.partner_bank_id.bank_bic:
                raise UserError(
                    _(
                        "La cuenta bancaria del Proveedor %s no tiene establecido el SWIFT."
                    )
                    % line.partner_id.name
                )
            # 30 - 63 IBAN
            if (
                self.payment_mode_id.conf_sabadell_type == "58"
                and line.partner_bank_id.acc_type != "iban"
            ):
                raise UserError(
                    _("La Cuenta del Proveedor: %s tiene que estar en formato IBAN.")
                    % line.partner_id.name
                )

    def _sab_registro_01(self):
        # Caracteres 1 y 2-3
        text = "1  "
        # 4 - 43 Nombre ordenante
        text += self._sab_convert_text(self.company_partner_bank_id.acc_holder_name, 40)
        # 44 - 51 Fecha de proceso
        text += (
            fields.Date.today().strftime("%Y%m%d")
            if self.date_prefered != "fixed"
            else self.date_scheduled.replace("-", "")
        )
        # 52 - 60 NIF
        vat = self.company_partner_bank_id.partner_id.vat
        if self.company_partner_bank_id.partner_id.country_id.code in vat:
            vat = vat.replace(
                self.company_partner_bank_id.partner_id.country_id.code, ""
            )
        text += self._sab_convert_text(vat, 9, "left")
        # 61 - 62 Tipo de Lote
        text += "65"
        # 63 - 64 Forma de envío
        text += "B"
        # 64 - 83 Cuenta de cargo
        cuenta = self.company_partner_bank_id.acc_number.replace(" ", "")
        if self.company_partner_bank_id.acc_type != "bank":
            cuenta = cuenta[4:]
        text += cuenta
        # 84 - 95 Contrato BSConfirming
        text += self.payment_mode_id.contrato_bsconfirming
        # 96 - 99 Codigo fichero
        text += "KF01"
        # 100 - 102 Codigo divisa
        text += self.company_currency_id.name
        text += "\r\n"
        return text

    def _sab_registro_02(self, line):
        # 1 Codigo registro
        text = "2"
        # 2 - 16 Codigo Proveedor
        text += self._sab_convert_text(line.partner_id.ref, 15)
        # 17 - 18 Tipo de documento
        text += "02"
        # 19 - 30 Documento identificativo
        text += self._sab_convert_text(line.partner_id.vat, 12)
        # 31 Forma de pago
        forma_pago_value = {"56": "T", "57": "C", "58": "E"}
        forma_pago = forma_pago_value[self.payment_mode_id.conf_sabadell_type]
        text += forma_pago
        # 32 - 51 Cuenta
        cuenta = (
            line.partner_bank_id.acc_number.replace(" ", "")
            if forma_pago == "T" and line.partner_bank_id.acc_type == "bank"
            else ""
        )
        text += self._sab_convert_text(cuenta, 20)
        # 52 - 66 Num Factura
        text += self._sab_convert_text(line.communication, 15)
        # 67 - 81 Importe de la factura
        text += self._sab_convert_text(str(line.amount_currency), 14, "left")
        signo_factura = "+" if line.amount_currency >= 0 else "-"
        text += signo_factura
        # 82 - 89 Fecha factura
        text += str(line.date).replace("-", "")
        # 90 - 97 Fecha vencimiento
        # fecha_vencimiento = 8 * ' '
        text += str(line.date).replace("-", "")
        # 98 - 127 Referencia factura ordenante
        text += self._sab_convert_text(line.communication.replace("-", ""), 30)
        # 128 - Barrado cheque
        barrado_cheque = "S" if forma_pago == "C" else " "
        text += barrado_cheque
        # 129 - 136 fecha emision pagaré
        text += self._sab_convert_text("", 8)
        # 137 -144 fecha vencimiento pagaré
        text += self._sab_convert_text("", 8)
        # 145 tipo pagare
        text += " "
        # 146 - 175 IBAN
        iban = (
            line.partner_bank_id.acc_number.replace(" ", "")
            if forma_pago == "T" and line.partner_bank_id.acc_type == "iban"
            else ""
        )
        text += self._sab_convert_text(iban, 30)
        # 176 Reservado
        text += self._sab_convert_text("", 125)
        text += "\r\n"
        return text

    def _sab_registro_03(self, line):
        # 1 Codigo registro
        text = "3"
        # 2 - 40 Nombre Proveedor
        text += self._sab_convert_text(line.partner_id.name, 40)
        # 42 - 43 Idioma proveedor
        idioma_pro = "08" if line.partner_id.lang == "es_ES" else "13"
        text += idioma_pro
        # 44 - 110 Domicilio
        text += self._sab_convert_text(line.partner_id.street, 67)
        # 111 - 150 Ciudad
        text += self._sab_convert_text(line.partner_id.city, 40)
        # 151- 155 CP
        text += self._sab_convert_text(line.partner_id.zip, 5)
        # 156 - 161 Reservado no se utiliza
        text += self._sab_convert_text("", 6)
        # 162 - 176 Telefono
        telefono_pro = (
            line.partner_id.phone.replace(" ", "").replace("+", "")
            if line.partner_id.phone
            else ""
        )
        text += self._sab_convert_text(telefono_pro, 15)
        # 177 - 191 fax
        text += self._sab_convert_text("", 15)
        # 192 - 251 Correo
        text += self._sab_convert_text(line.partner_id.email, 60)
        # 252 Tipo envio informacion
        # Por correo 1, por fax 2, por email 3
        text += self.payment_mode_id.tipo_envio_info
        # 253 - 254 Codigo pais
        text += line.partner_id.country_id.code
        # 255 -256 Codigo pais residencia no se usa
        text += "  "
        # 257 --- Reservado
        text += self._sab_convert_text("", 44)
        text += "\r\n"
        return text

    def _sab_registro_04(self, line):
        # 1 Codigo registro
        text = "4"
        # 2 -16 Codigo proveedor
        codigo_pro = line.partner_id.ref if line.partner_id.ref else 15 * " "
        text += codigo_pro
        # 17 - 18 Codigo Pais
        text += line.partner_id.country_id.code
        # 19 - 29 SWIFT
        text += self._sab_convert_text(line.partner_bank_id.bank_bic, 11)
        # 30 - 63 IBAN
        iban = (
            line.partner_bank_id.acc_number.replace(" ", "")
            if (
                self.payment_mode_id.conf_sabadell_type == "58"
                and line.partner_bank_id.acc_type == "iban"
            )
            else ""
        )
        text += self._sab_convert_text(iban, 34)
        # 64 - 69 Codigo estadistico
        text += self.payment_mode_id.codigo_estadistico
        # 70 Divisa
        text += self.company_currency_id.name
        text += "\r\n"
        return text

    def _sab_registro_05(self):
        text = "5"
        # 2 - 10 NIF
        text += self._sab_convert_text(
            self.company_partner_bank_id.partner_id.vat[2:], 9, "left"
        )
        # 11 - 17 Total ordenes
        text += self._sab_convert_text(str(len(self.payment_line_ids)), 7, "left")
        # 18 - 32  - Total importes
        total_amount = sum(self.payment_line_ids.mapped("amount_currency"))
        text += self._sab_convert_text(str(total_amount), 14, "left")
        importe_sign = "+" if total_amount >= 0 else "-"
        text += importe_sign
        # 60-72 - Libre
        text += self._sab_convert_text("", 268)
        text += "\r\n"
        return text
