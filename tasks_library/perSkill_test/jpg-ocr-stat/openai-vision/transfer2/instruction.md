## Task Description

You are given receipt images in `/app/workspace/dataset/transfer2_receipts`.

Create a CSV file at:

- `/root/transfer2_amount_bands.csv`

Classify each extracted receipt total into one of the following bands:

- `low_lt_20`: amount < 20.00
- `mid_20_to_99_99`: 20.00 <= amount < 100.00
- `high_ge_100`: amount >= 100.00

Output format rules:

1. Header must be exactly: `band,receipt_count,total_amount,share_percent`
2. Output rows must be in this fixed order:
   - `low_lt_20`
   - `mid_20_to_99_99`
   - `high_ge_100`
3. `receipt_count` is an integer.
4. `total_amount` must be a decimal string with two digits.
5. `share_percent` must be a decimal string with two digits (percentage of grand total amount).
6. Do not add extra columns or rows.
