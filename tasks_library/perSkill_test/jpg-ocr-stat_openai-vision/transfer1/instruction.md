## Task Description

Receipt images are provided in `/app/workspace/dataset/transfer1_receipts`.

Create a JSON file at:

- `/root/transfer1_monthly_totals.json`

The JSON must be an array of objects. Each object must contain exactly:

- `month` (format `YYYY-MM`)
- `receipt_count` (integer)
- `total_amount` (string with exactly two decimals)

Rules:

1. Use one object per month present in the input images.
2. Group by the extracted receipt date month.
3. Sort objects by `month` ascending.
4. Keep `total_amount` as a decimal string with two digits after the decimal point.
5. Do not add extra keys.

This task emphasizes converting image-derived receipt totals into a monthly finance summary.
