## Task description

In `/app/workspace/dataset/img`, there is a collection of scanned receipt images.

Read all image files in that directory, extract the receipt date and total amount from each image, and write:

`/app/workspace/transfer1_monthly_summary.json`

The output must be valid JSON with this exact schema:

```json
{
  "generated_from": "/app/workspace/dataset/img",
  "monthly_totals": [
    {
      "month": "YYYY-MM",
      "receipt_count": 0,
      "sum_total_amount": "0.00"
    }
  ],
  "grand_total_amount": "0.00"
}
```

Rules:

1. `monthly_totals` must be sorted by `month` ascending.
2. `receipt_count` is the number of receipts in that month.
3. `sum_total_amount` and `grand_total_amount` must be strings with exactly two decimal places.
4. `generated_from` must be exactly `/app/workspace/dataset/img`.
5. Do not add extra top-level keys.

The verifier compares your JSON output with an oracle JSON file.
