#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import Workbook

INPUT_PATH = "/app/workspace/visits.json"
OUTPUT_PATH = "/app/workspace/transfer2.xlsx"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

by_day = {}
for row in data:
    day = row["date"]
    patients = int(row["patients"])
    wait = Decimal(str(row["avg_wait_min"]))
    if day not in by_day:
        by_day[day] = {"patients": 0, "weighted_sum": Decimal("0")}
    by_day[day]["patients"] += patients
    by_day[day]["weighted_sum"] += Decimal(patients) * wait

ordered_days = sorted(by_day.keys())

wb = Workbook()
ws = wb.active
ws.title = "daily_summary"
ws.append(["date", "total_patients", "weighted_wait_min"])

for day in ordered_days:
    total_patients = by_day[day]["patients"]
    if total_patients == 0:
        weighted_wait = None
    else:
        avg = by_day[day]["weighted_sum"] / Decimal(total_patients)
        weighted_wait = f"{avg.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):.1f}"
    ws.append([day, str(total_patients), weighted_wait])

wb.save(OUTPUT_PATH)
PY
