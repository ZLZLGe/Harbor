## Task description

In `/app/workspace/dataset/img`, there is a collection of scanned receipt images.

Read all image files in that directory, extract the receipt date and total amount from each image, and write:

`/app/workspace/transfer3_expense_ranking.json`

The output must be valid JSON with this exact schema:

```json
{
  "generated_from": "/app/workspace/dataset/img",
  "overall_total_amount": "0.00",
  "top_5_receipts": [
    {
      "filename": "000.jpg",
      "date": "YYYY-MM-DD",
      "total_amount": "0.00"
    }
  ],
  "bottom_5_receipts": [
    {
      "filename": "000.jpg",
      "date": "YYYY-MM-DD",
      "total_amount": "0.00"
    }
  ]
}
```

Rules:

1. Use only receipts where both `date` and `total_amount` are extracted.
2. `top_5_receipts` must be sorted by `total_amount` descending, then by `filename` ascending.
3. `bottom_5_receipts` must be sorted by `total_amount` ascending, then by `filename` ascending.
4. `overall_total_amount` must be a string with exactly two decimal places.
5. `generated_from` must be exactly `/app/workspace/dataset/img`.
6. Do not add extra top-level keys.

The verifier compares your JSON output with an oracle JSON file.
