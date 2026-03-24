#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import Workbook


INPUT_DIR = Path("/app/workspace/inbox/receipts_txt")
OUTPUT_PATH = Path("/app/workspace/receipt_rollup.xlsx")

DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{4}/\d{2}/\d{2})\b"),
    re.compile(r"\b(\d{2}/\d{2}/\d{4})\b"),
    re.compile(r"\b(\d{2}-\d{2}-\d{4})\b"),
]

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
]

TOTAL_KEYWORDS = [
    "GRAND TOTAL",
    "TOTAL RM",
    "TOTAL AMOUNT",
    "AMOUNT DUE",
    "NETT TOTAL",
    "TOTAL DUE",
]

EXCLUDE_KEYWORDS = [
    "SUBTOTAL",
    "SUB TOTAL",
    "TAX",
    "GST",
    "SST",
    "CHANGE",
    "DISCOUNT",
]

AMOUNT_RE = re.compile(r"(\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})")


def extract_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        for match in pattern.findall(text):
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(match, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


def normalize_amount(raw: str) -> str | None:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    return f"{value:.2f}"


def extract_total(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        upper = line.upper()
        if any(keyword in upper for keyword in EXCLUDE_KEYWORDS):
            continue
        if any(keyword in upper for keyword in TOTAL_KEYWORDS):
            matches = AMOUNT_RE.findall(line)
            if matches:
                amount = normalize_amount(matches[-1])
                if amount is not None:
                    return amount
            if index + 1 < len(lines):
                next_matches = AMOUNT_RE.findall(lines[index + 1])
                if next_matches:
                    amount = normalize_amount(next_matches[-1])
                    if amount is not None:
                        return amount
    return None


rows: list[list[str | None]] = [["filename", "date", "total_amount"]]

for path in sorted(INPUT_DIR.glob("*.txt")):
    text = path.read_text(encoding="utf-8")
    rows.append([
        path.name,
        extract_date(text),
        extract_total(text),
    ])

workbook = Workbook()
sheet = workbook.active
sheet.title = "results"

for row in rows:
    sheet.append(row)

workbook.save(OUTPUT_PATH)
PY
