Read `/root/vendor_invoices.pdf`. It is a three-page invoice packet with repeated page headers and one duplicate invoice entry.

Extract every invoice from the packet and write `/root/workspace/invoice_ledger.csv` with this exact header:

`invoice_no,vendor,due_date,amount`

Rules:

- Use only the data present in the PDF.
- Keep these fields for each invoice: invoice number, vendor, due date, and amount due.
- Deduplicate by `invoice_no`. The duplicate entries in the packet are identical and should appear only once in the final ledger.
- Normalize `due_date` to `YYYY-MM-DD`.
- Normalize `amount` to a plain decimal string with exactly two digits after the decimal point, without currency symbols or thousands separators.
- Sort rows by `due_date` ascending, then by `invoice_no` ascending.
