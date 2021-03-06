.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

================================
Presentación del Modelo AEAT 216
================================

Modelo 216 de la AEAT. IRNR. Impuesto sobre la Renta de no Residentes. Rentas
obtenidas sin mediación de establecimiento permanente. Retenciones e ingresos
a cuenta.

Configuración
=============

Debemos indicar los proveedores que son no residentes, en la ficha de la
empresa: Contabilidad > Proveedores > Proveedores, pestaña de Contabilidad.
El campo "Es no residente" tiene que estar marcado para que las retenciones
realizadas a este proveedor se incluyan en el modelo 216.

Uso
===

Para crear un modelo:

1. Ir a Contabilidad > Informe > Informes legales > Declaraciones AEAT > Modelo 216.
2. Pulsar en el botón "Crear".
3. Seleccionar el año y el tipo de período. Las fechas incluidas se calculan
   automáticamente.
4. Seleccionar el tipo de declaración.
5. Rellenar el teléfono de contacto, necesario para la exportacion BOE.
6. Guardar y pulsar en el botón "Calcular".
7. Rellenar (si es necesario) aquellos campos que Odoo no calcula automáticamente:

   * Rentas no sometidas a retención/ingreso a cuenta: [04] Nº de rentas y [05] Base de retenciones
   * Resultados a ingresar anteriores: [06]

8. Cuando los valores sean los correctos, pulsar en el botón "Confirmar"
9. Podemos exportar en formato BOE para presentarlo telemáticamente en el portal
   de la AEAT

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Pruébalo en Runbot
   :target: https://runbot.odoo-community.org/runbot/189/9.0

Créditos
========

Contribuidores
--------------

* Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
* Ainara Galdona <ainara.galdona@avanzosc.es>
* Antonio Espinosa <antonio.espinosa@tecnativa.com>


Financiadores
-------------
La migración de este módulo forma parte de una campaña de migración de la
localización española que ha sido posible gracias a la colaboración económica
de las siguientes empresas (por orden alfabético):

* `Aizean evolution <http://www.aizean.com>`_
* `Aselcis consulting <https://www.aselcis.com>`_
* `AvanzOSC <http://avanzosc.es>`_
* `Diagram software <http://diagram.es>`_
* `Domatix <http://www.domatix.com>`_
* `Eficent <http://www.eficent.com>`_
* `FactorLibre <http://factorlibre.com>`_
* `Fairhall solutions <http://www.fairhall.es>`_
* `GAFIC SLP <http://www.gafic.com>`_
* `Incaser <http://www.incaser.es>`_
* `Ingeos <http://www.ingeos.es>`_
* `Nubistalia <http://www.nubistalia.es>`_
* `Punt sistemes <http://www.puntsistemes.es>`_
* `Praxya <http://praxya.com>`_
* `Reeng <http://www.reng.es>`_
* `Soluntec <http://www.soluntec.es>`_
* `Tecnativa <https://www.tecnativa.com>`_
* `Trey <https://www.trey.es>`_
* `Vicent Cubells <http://vcubells.net>`_

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
