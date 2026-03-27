## Task Description

`/app/workspace/receipts.csv` contains receipt rows extracted from upstream processing.

Create `/app/workspace/similar.xlsx` with exactly one sheet named `results` and exactly these columns:

- `filename`
- `date`
- `total_amount`

Rules:

1. Input columns are `filename,date_raw,total_text`.
2. Normalize `date_raw` to `YYYY-MM-DD` if parseable.
3. Normalize `total_text` to a string with exactly two decimals.
4. If a date or amount cannot be parsed, leave that output cell blank.
5. Sort output rows by `filename` ascending.
6. The first row must be the header. Do not create extra sheets, columns, or rows.
