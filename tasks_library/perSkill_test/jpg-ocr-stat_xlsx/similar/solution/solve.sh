#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from openpyxl import Workbook

INPUT_PATH = "/app/workspace/receipts.csv"
OUTPUT_PATH = "/app/workspace/similar.xlsx"

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
]
AMOUNT_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def parse_date(raw: str):
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_amount(raw: str):
    text = (raw or "").replace("RM", "").replace("$", "").strip()
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    token = match.group(0).replace(",", "")
    try:
        value = Decimal(token)
    except InvalidOperation:
        return None
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


rows = []
with open(INPUT_PATH, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for record in reader:
        rows.append(
            {
                "filename": (record.get("filename") or "").strip(),
                "date": parse_date(record.get("date_raw") or ""),
                "total_amount": parse_amount(record.get("total_text") or ""),
            }
        )

rows.sort(key=lambda row: row["filename"])

wb = Workbook()
ws = wb.active
ws.title = "results"
ws.append(["filename", "date", "total_amount"])
for row in rows:
    ws.append([row["filename"], row["date"], row["total_amount"]])

wb.save(OUTPUT_PATH)
PY
