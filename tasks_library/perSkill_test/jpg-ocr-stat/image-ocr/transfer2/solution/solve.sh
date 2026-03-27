#!/bin/bash
set -e

python3 - <<'PY'
import json
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from ocr_core import extract_data_from_images

input_dir = "/app/workspace/dataset/img"
output_path = "/app/workspace/transfer2_quarterly_summary.json"


def q2(x: Decimal) -> str:
    return f"{x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def quarter_of(date_str: str) -> str:
    year = date_str[:4]
    month = int(date_str[5:7])
    q = (month - 1) // 3 + 1
    return f"{year}-Q{q}"

rows = extract_data_from_images(input_dir)
quarter_count = defaultdict(int)
quarter_sum = defaultdict(Decimal)

for filename in sorted(rows.keys()):
    date_value = rows[filename].get("date")
    amount_value = rows[filename].get("total_amount")
    if not date_value or not amount_value:
        continue
    q = quarter_of(date_value)
    amount = Decimal(str(amount_value))
    quarter_count[q] += 1
    quarter_sum[q] += amount

quarterly_totals = []
for q in sorted(quarter_count.keys()):
    total = quarter_sum[q]
    count = quarter_count[q]
    avg = total / Decimal(count)
    quarterly_totals.append(
        {
            "quarter": q,
            "receipt_count": count,
            "sum_total_amount": q2(total),
            "average_total_amount": q2(avg),
        }
    )

highest_quarter_key = None
highest_sum = Decimal("-1")
for q in sorted(quarter_sum.keys()):
    s = quarter_sum[q]
    if s > highest_sum:
        highest_sum = s
        highest_quarter_key = q

result = {
    "generated_from": input_dir,
    "quarterly_totals": quarterly_totals,
    "highest_quarter": {
        "quarter": highest_quarter_key,
        "sum_total_amount": q2(highest_sum),
    },
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY

echo "Solution complete."
