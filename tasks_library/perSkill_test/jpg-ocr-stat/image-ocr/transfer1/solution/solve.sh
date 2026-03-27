#!/bin/bash
set -e

python3 - <<'PY'
import json
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from ocr_core import extract_data_from_images

input_dir = "/app/workspace/dataset/img"
output_path = "/app/workspace/transfer1_monthly_summary.json"


def q2(x: Decimal) -> str:
    return f"{x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"

rows = extract_data_from_images(input_dir)
monthly_count = defaultdict(int)
monthly_sum = defaultdict(Decimal)
grand = Decimal("0")

for filename in sorted(rows.keys()):
    date_value = rows[filename].get("date")
    amount_value = rows[filename].get("total_amount")
    if not date_value or not amount_value:
        continue
    month = date_value[:7]
    amount = Decimal(str(amount_value))
    monthly_count[month] += 1
    monthly_sum[month] += amount
    grand += amount

monthly_totals = []
for month in sorted(monthly_count.keys()):
    monthly_totals.append(
        {
            "month": month,
            "receipt_count": monthly_count[month],
            "sum_total_amount": q2(monthly_sum[month]),
        }
    )

result = {
    "generated_from": input_dir,
    "monthly_totals": monthly_totals,
    "grand_total_amount": q2(grand),
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY

echo "Solution complete."
