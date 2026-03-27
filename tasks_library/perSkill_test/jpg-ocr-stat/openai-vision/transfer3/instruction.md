## Task Description

Receipt images are available in `/app/workspace/dataset/transfer3_receipts`.

Create a TSV report at:

- `/root/transfer3_weekday_report.tsv`

Required columns (tab-separated):

- `weekday`
- `receipt_count`
- `total_amount`
- `average_amount`

Rules:

1. Group receipts by weekday inferred from extracted receipt date.
2. Output rows for weekdays in this order: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`.
3. Include weekday rows even when count is zero.
4. Add one final row named `TOTAL` with overall count/total/average.
5. `total_amount` and `average_amount` must use exactly two decimal places.
6. No extra columns, comments, or footer text.
