- The current version of the Intrastat reporting module is only based on
  invoices. Since associated stock moves are not taken into
  consideration, it is possible that manual corrections are required,
  e.g.
  - Product movements without invoices are not included in the current
    version of this module and must be added manually to the report
    lines before generating the declaration.
- The current version of the Intrastat reporting module does not perform
  a cross-check with the VAT declaration.
- Add tests.
- A return of goods is declared in the month of its credit note, not in the
  month of the return picking. It is detected through the order line of the
  credit note: a later credit note without return on an order line that had a
  return is declared as a return too, and goods returned without a sale or
  purchase order must be added by hand.
