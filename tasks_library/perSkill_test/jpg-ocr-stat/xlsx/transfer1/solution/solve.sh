#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import Workbook

INPUT_PATH = "/app/workspace/stock.csv"
OUTPUT_PATH = "/app/workspace/transfer1.xlsx"

rows = []
with open(INPUT_PATH, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for item in reader:
        sku = (item.get("sku") or "").strip()
        on_hand = int(item.get("on_hand") or 0)
        reorder_point = int(item.get("reorder_point") or 0)
        unit_cost = Decimal((item.get("unit_cost") or "0").strip())
        order_qty = max(reorder_point - on_hand, 0)
        reorder_cost = (Decimal(order_qty) * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rows.append(
            {
                "sku": sku,
                "on_hand": str(on_hand),
                "reorder_point": str(reorder_point),
                "order_qty": str(order_qty),
                "reorder_cost": f"{reorder_cost:.2f}",
            }
        )

rows.sort(key=lambda row: (-int(row["order_qty"]), row["sku"]))

wb = Workbook()
ws = wb.active
ws.title = "plan"
ws.append(["sku", "on_hand", "reorder_point", "order_qty", "reorder_cost"])
for row in rows:
    ws.append([row["sku"], row["on_hand"], row["reorder_point"], row["order_qty"], row["reorder_cost"]])

wb.save(OUTPUT_PATH)
PY
