#!/bin/bash
set -euo pipefail

PDF_FILE="${PDF_FILE:-/root/vendor_price_archive.pdf}"
CSV_FILE="${CSV_FILE:-/root/current_procurement_list.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/vendor_diff_report.json}"
export PDF_FILE CSV_FILE OUTPUT_FILE

python3 - <<'PY'
import csv
import json
import os
import re
from decimal import Decimal
from pathlib import Path

PDF_FILE = Path(os.environ["PDF_FILE"])
CSV_FILE = Path(os.environ["CSV_FILE"])
OUTPUT_FILE = Path(os.environ["OUTPUT_FILE"])


def decode_pdf_literal(value):
    return (
        value.replace(r"\\", "\\")
        .replace(r"\(", "(")
        .replace(r"\)", ")")
    )


def normalize_number(value):
    decimal_value = Decimal(value)
    if decimal_value == decimal_value.to_integral():
        return int(decimal_value)
    return float(decimal_value)


def extract_archived_rows(pdf_path):
    raw_text = pdf_path.read_bytes().decode("latin-1", errors="ignore")
    literals = re.findall(r"\(((?:\\.|[^\\()])*)\)\s*Tj", raw_text)

    rows = {}
    for literal in literals:
        line = decode_pdf_literal(literal).strip()
        if not re.match(r"^VND-\d{4}\s+\|", line):
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 5:
            continue

        sku, product_name, unit_price, min_order_qty, _category = parts
        rows[sku] = {
            "sku": sku,
            "product_name": product_name,
            "unit_price": Decimal(unit_price),
            "min_order_qty": int(min_order_qty),
        }
    return rows


def read_current_rows(csv_path):
    rows = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows[row["sku"]] = {
                "sku": row["sku"],
                "product_name": row["product_name"],
                "unit_price": Decimal(row["unit_price"]),
                "min_order_qty": int(row["min_order_qty"]),
            }
    return rows


def build_report(archived_rows, current_rows):
    archived_skus = set(archived_rows)
    current_skus = set(current_rows)

    report = {
        "discontinued_skus": sorted(archived_skus - current_skus),
        "changed_items": [],
    }

    for sku in sorted(archived_skus & current_skus):
        archived = archived_rows[sku]
        current = current_rows[sku]
        for field in ("min_order_qty", "unit_price"):
            if archived[field] == current[field]:
                continue
            report["changed_items"].append(
                {
                    "sku": sku,
                    "field": field,
                    "old_value": normalize_number(str(archived[field])),
                    "new_value": normalize_number(str(current[field])),
                }
            )

    report["changed_items"].sort(key=lambda item: (item["sku"], item["field"]))
    return report


def main():
    report = build_report(
        extract_archived_rows(PDF_FILE),
        read_current_rows(CSV_FILE),
    )
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PY
