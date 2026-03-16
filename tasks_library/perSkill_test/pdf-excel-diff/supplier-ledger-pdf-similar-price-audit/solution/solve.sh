#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import re
from pathlib import Path

import pdfplumber

PDF_FILE = Path("/root/supplier_ledger_archive.pdf")
CSV_FILE = Path("/root/supplier_prices_current.csv")
OUTPUT_FILE = Path("/root/supplier_price_diff.json")
EXPECTED_COLUMNS = [
    "SKU",
    "Description",
    "Category",
    "Unit",
    "Currency",
    "UnitPrice",
    "LeadDays",
    "MOQ",
]
NUMERIC_FLOAT_FIELDS = {"UnitPrice"}
NUMERIC_INT_FIELDS = {"LeadDays", "MOQ"}
SKU_PATTERN = re.compile(r"^SUP-\d{4}$")


def clean_cell(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def convert_value(field, value):
    cleaned = clean_cell(value)
    if field in NUMERIC_FLOAT_FIELDS:
        return round(float(cleaned), 2)
    if field in NUMERIC_INT_FIELDS:
        return int(float(cleaned))
    return cleaned


def extract_archive_rows(pdf_path):
    rows_by_sku = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for raw_row in table:
                    if not raw_row:
                        continue

                    cleaned_row = [clean_cell(cell) for cell in raw_row]
                    if not any(cleaned_row):
                        continue

                    if cleaned_row[: len(EXPECTED_COLUMNS)] == EXPECTED_COLUMNS:
                        continue

                    if not SKU_PATTERN.match(cleaned_row[0]):
                        continue

                    cleaned_row = (cleaned_row + [""] * len(EXPECTED_COLUMNS))[: len(EXPECTED_COLUMNS)]
                    row = {
                        column: convert_value(column, cleaned_row[index])
                        for index, column in enumerate(EXPECTED_COLUMNS)
                    }
                    rows_by_sku[row["SKU"]] = row
    return rows_by_sku


def read_current_rows(csv_path):
    rows_by_sku = {}
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = {
                column: convert_value(column, raw_row[column])
                for column in EXPECTED_COLUMNS
            }
            rows_by_sku[row["SKU"]] = row
    return rows_by_sku


def compare_rows(archive_rows, current_rows):
    discontinued = sorted(set(archive_rows) - set(current_rows))
    updated = []

    for sku in sorted(set(archive_rows) & set(current_rows)):
        archive_row = archive_rows[sku]
        current_row = current_rows[sku]

        for field in EXPECTED_COLUMNS[1:]:
            if archive_row[field] != current_row[field]:
                updated.append(
                    {
                        "sku": sku,
                        "field": field,
                        "old_value": archive_row[field],
                        "new_value": current_row[field],
                    }
                )

    updated.sort(key=lambda item: (item["sku"], item["field"]))
    return {
        "discontinued_skus": discontinued,
        "updated_products": updated,
    }


def main():
    archive_rows = extract_archive_rows(PDF_FILE)
    current_rows = read_current_rows(CSV_FILE)
    result = compare_rows(archive_rows, current_rows)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
PY
