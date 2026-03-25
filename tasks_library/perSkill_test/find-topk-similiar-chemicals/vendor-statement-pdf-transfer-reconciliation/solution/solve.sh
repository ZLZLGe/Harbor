#!/bin/bash

set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import csv
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pdfplumber


INPUT_PATH = Path("/root/data/vendor_statement_bundle")
OUTPUT_PATH = Path("/root/workspace/reconciliation.csv")
AMOUNT_QUANT = Decimal("0.01")
VENDOR_PATTERN = re.compile(r"^Vendor:\s+(?P<vendor_id>[^|]+)\|\s*(?P<vendor_name>.+)$")


def normalize_amount(value: Decimal) -> str:
    return str(value.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP))


aggregates: dict[str, dict[str, Decimal | str]] = {}
current_vendor_id = None
current_vendor_name = None

with pdfplumber.open(str(INPUT_PATH)) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            vendor_match = VENDOR_PATTERN.match(line)
            if vendor_match:
                current_vendor_id = vendor_match.group("vendor_id").strip()
                current_vendor_name = vendor_match.group("vendor_name").strip()
                aggregates.setdefault(
                    current_vendor_id,
                    {
                        "vendor_name": current_vendor_name,
                        "amount_due": Decimal("0.00"),
                        "amount_paid": Decimal("0.00"),
                    },
                )
                continue

            if not line.startswith(("INV-", "CRM-")):
                continue

            if current_vendor_id is None or current_vendor_name is None:
                raise RuntimeError(f"Row without vendor context: {line}")

            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 5:
                raise RuntimeError(f"Unexpected row format: {line}")

            charge = Decimal(parts[2])
            paid = Decimal(parts[3])
            record = aggregates[current_vendor_id]
            record["vendor_name"] = current_vendor_name
            record["amount_due"] += charge
            record["amount_paid"] += paid

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["vendor_id", "vendor_name", "amount_due", "amount_paid", "difference"])

    for vendor_id in sorted(aggregates):
        record = aggregates[vendor_id]
        amount_due = record["amount_due"]
        amount_paid = record["amount_paid"]
        difference = amount_due - amount_paid
        writer.writerow(
            [
                vendor_id,
                record["vendor_name"],
                normalize_amount(amount_due),
                normalize_amount(amount_paid),
                normalize_amount(difference),
            ]
        )
PY
