## Task Description

You are given scanned receipt images in `/app/workspace/dataset/similar_receipts`.

Generate a CSV ledger at:

- `/root/similar_receipt_rows.csv`

Output requirements:

1. The file must use UTF-8 encoding.
2. Header must be exactly:
   - `filename,date,total_amount`
3. Include one row per image file.
4. Rows must be ordered by filename ascending.
5. `date` format must be `YYYY-MM-DD`.
6. `total_amount` must keep exactly two decimal places.
7. If extraction fails for a field, leave it empty.
8. Do not write extra columns.

Focus on the receipt date and final payable amount for each image.
