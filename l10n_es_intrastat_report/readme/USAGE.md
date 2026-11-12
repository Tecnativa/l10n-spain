1.  Go to *Invocing \> Reporting \> Intrastat \> Spanish Intrastat
    Product Declaration*.

2.  Create a new record.

3.  Select or input following data:

    - Year
    - Month
    - Type: for selecting if arrivals or dispatches.
    - Reporting level: standard or extended.
    - Action:
      - if "Nihil", no recomputation is possible and the report is
        considered empty.
      - if "Replace", everything is recomputed.
      - if "Append", only new lines are added.

4.  Click on "Generate Lines from invoices" for populating transaction
    lines.

    You can review them on "Transactions" page of the report.

5.  Click on "Generate Declaration Lines" for populating the lines that
    summarize transactions and will be the source for the exports.

    You can review them on "Declaration Lines" page.

6.  Click on "Generate CSV Declaration Line" for getting the CSV for
    declaring the report in AEAT.

7.  Click on "Excel Export" for having the information in a spreadsheet.

Credit notes are declared only for the goods physically returned: a line of
a credit note whose sale or purchase order line has a done return picking is
declared in the opposite flow (arrivals for sales, dispatches for purchases)
with the transaction code 21. Credit notes without return of goods (price
discounts, rappels, damaged goods kept by the customer) are not declared.
