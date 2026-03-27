## Task description

In `/app/workspace/dataset/img`, there is a folder of scanned receipt images.

Read all image files under that path, extract each receipt date and total amount, and write an Excel file to:

`/app/workspace/similar_receipt_ledger.xlsx`

The workbook must contain exactly one sheet named `ledger` with exactly 4 columns:

- `filename`: source filename (for example `000.jpg`)
- `date`: extracted date in ISO format `YYYY-MM-DD`
- `total_amount`: monetary value as a string with exactly two decimal places
- `year_month`: derived from date as `YYYY-MM` (if `date` is missing, set this to null)

Rules:

1. The first row must be the header row with the exact column names above.
2. Data rows must be ordered by `filename` ascending.
3. If extraction fails for `date` or `total_amount`, write null for that field.
4. Do not create extra sheets, columns, or rows.

The verifier compares your workbook with an oracle workbook row by row.
