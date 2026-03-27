#!/bin/bash
set -e

python3 - <<'PY'
from openpyxl import Workbook
from ocr_core import extract_data_from_images

input_dir = "/app/workspace/dataset/img"
output_path = "/app/workspace/similar_receipt_ledger.xlsx"

results = extract_data_from_images(input_dir)

wb = Workbook()
ws = wb.active
ws.title = "ledger"
ws.append(["filename", "date", "total_amount", "year_month"])

for filename in sorted(results.keys()):
    row = results[filename]
    date_value = row.get("date")
    total_value = row.get("total_amount")
    year_month = date_value[:7] if date_value else None
    ws.append([filename, date_value, total_value, year_month])

wb.save(output_path)
PY

echo "Solution complete."
