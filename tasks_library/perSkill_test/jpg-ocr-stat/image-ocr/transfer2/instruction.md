## Task description

In `/app/workspace/dataset/img`, there is a collection of scanned receipt images.

Read all image files in that directory, extract the receipt date and total amount from each image, and write:

`/app/workspace/transfer2_quarterly_summary.json`

The output must be valid JSON with this exact schema:

```json
{
  "generated_from": "/app/workspace/dataset/img",
  "quarterly_totals": [
    {
      "quarter": "YYYY-QN",
      "receipt_count": 0,
      "sum_total_amount": "0.00",
      "average_total_amount": "0.00"
    }
  ],
  "highest_quarter": {
    "quarter": "YYYY-QN",
    "sum_total_amount": "0.00"
  }
}
```

Rules:

1. `quarterly_totals` must be sorted by `quarter` ascending.
2. `sum_total_amount` and `average_total_amount` must be strings with exactly two decimal places.
3. `generated_from` must be exactly `/app/workspace/dataset/img`.
4. `highest_quarter` must be the quarter with the largest `sum_total_amount`.
5. Do not add extra top-level keys.

The verifier compares your JSON output with an oracle JSON file.
