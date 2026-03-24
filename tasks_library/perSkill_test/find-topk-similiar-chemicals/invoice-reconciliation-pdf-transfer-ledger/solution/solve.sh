#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import csv
import re
from datetime import datetime

from pypdf import PdfReader

PDF_PATH = "/root/vendor_invoices.pdf"
OUTPUT_PATH = "/root/workspace/invoice_ledger.csv"

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%b %d, %Y",
    "%B %d, %Y",
]

PATTERN = re.compile(
    r"Invoice No:\s*(?P<invoice_no>[A-Z0-9-]+)\s+"
    r"Vendor:\s*(?P<vendor>.+?)\s+"
    r"Issue Date:\s*(?P<issue_date>.+?)\s+"
    r"Due Date:\s*(?P<due_date>.+?)\s+"
    r"Amount Due:\s*\$(?P<amount>[0-9,]+\.\d{2})",
    re.S,
)


def normalize_date(raw_value):
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(raw_value.strip(), date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unsupported date format: {raw_value}")


reader = PdfReader(PDF_PATH)
full_text = "\\n".join(page.extract_text() or "" for page in reader.pages)

ledger = {}
for match in PATTERN.finditer(full_text):
    invoice_no = match.group("invoice_no").strip()
    if invoice_no in ledger:
        continue
    ledger[invoice_no] = {
        "invoice_no": invoice_no,
        "vendor": match.group("vendor").strip(),
        "due_date": normalize_date(match.group("due_date")),
        "amount": match.group("amount").replace(",", ""),
    }

rows = sorted(ledger.values(), key=lambda row: (row["due_date"], row["invoice_no"]))

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["invoice_no", "vendor", "due_date", "amount"])
    writer.writeheader()
    writer.writerows(rows)
PY
