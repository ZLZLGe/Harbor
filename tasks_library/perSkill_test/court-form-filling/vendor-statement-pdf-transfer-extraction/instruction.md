Read the vendor statement file already placed in `/root`. Its basename is `vendor-statement`, and you should use its existing extension. Write `/root/invoice-summary.json`.

The output must be valid JSON with this shape:

```json
{
  "invoices": [
    {
      "invoice_number": "BR-4817",
      "statement_date": "2026-02-28",
      "due_date": "2026-03-02",
      "amount_due": "1245.50"
    }
  ]
}
```

Requirements:

- Include every open invoice shown anywhere in the statement file.
- Sort `invoices` by `invoice_number` in ascending order.
- Use `YYYY-MM-DD` for all dates.
- Format `amount_due` as a string with exactly two decimal places and no currency symbol or commas.
- Ignore paid balances, notes, totals, remittance instructions, and any other non-invoice lines.
