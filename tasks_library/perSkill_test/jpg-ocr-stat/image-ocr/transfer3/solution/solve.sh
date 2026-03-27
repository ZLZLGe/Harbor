#!/bin/bash
set -e

python3 - <<'PY'
import json
from decimal import Decimal, ROUND_HALF_UP
from ocr_core import extract_data_from_images

input_dir = "/app/workspace/dataset/img"
output_path = "/app/workspace/transfer3_expense_ranking.json"


def q2(x: Decimal) -> str:
    return f"{x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"

rows = extract_data_from_images(input_dir)
valid_rows = []
overall = Decimal("0")

for filename in sorted(rows.keys()):
    date_value = rows[filename].get("date")
    amount_value = rows[filename].get("total_amount")
    if not date_value or not amount_value:
        continue
    amount = Decimal(str(amount_value))
    overall += amount
    valid_rows.append(
        {
            "filename": filename,
            "date": date_value,
            "total_amount": q2(amount),
            "_amount": amount,
        }
    )

top_sorted = sorted(valid_rows, key=lambda x: (-x["_amount"], x["filename"]))[:5]
bottom_sorted = sorted(valid_rows, key=lambda x: (x["_amount"], x["filename"]))[:5]

for row in top_sorted:
    row.pop("_amount", None)
for row in bottom_sorted:
    row.pop("_amount", None)

result = {
    "generated_from": input_dir,
    "overall_total_amount": q2(overall),
    "top_5_receipts": top_sorted,
    "bottom_5_receipts": bottom_sorted,
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY

echo "Solution complete."
