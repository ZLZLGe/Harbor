#!/bin/bash
set -euo pipefail

cat > /tmp/solve_vendor_catalog.py <<'PY'
#!/usr/bin/env python3

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PDF_FILE = Path("/root/vendor_catalog_archive.pdf")
XLSX_FILE = Path("/root/vendor_pricebook_current.xlsx")
OUTPUT_FILE = Path("/root/vendor_catalog_diff.json")

HEADERS = ["SKU", "ItemName", "Category", "UnitPrice", "Currency", "PackSize", "LeadTimeDays"]
NUMERIC_FIELDS = {"UnitPrice", "PackSize", "LeadTimeDays"}


def decode_pdf_literal(value: str) -> str:
    return (
        value.replace(r"\\", "\\")
        .replace(r"\(", "(")
        .replace(r"\)", ")")
    )


def read_pdf_rows(path: Path):
    raw_text = path.read_bytes().decode("latin-1", errors="ignore")
    literals = [decode_pdf_literal(match) for match in re.findall(r"\((.*?)\)\s*Tj", raw_text, flags=re.DOTALL)]

    rows = []
    for line in literals:
        if not line.startswith("SKU-"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != len(HEADERS):
            continue
        row = dict(zip(HEADERS, parts))
        row["UnitPrice"] = float(row["UnitPrice"])
        row["PackSize"] = int(row["PackSize"])
        row["LeadTimeDays"] = int(row["LeadTimeDays"])
        rows.append(row)
    return rows


def read_xlsx_rows(path: Path):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        xml_data = zf.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(xml_data)
    rows = []
    for row_node in root.findall(".//a:sheetData/a:row", ns):
        values = []
        for cell in row_node.findall("a:c", ns):
            inline = cell.find("a:is/a:t", ns)
            value_node = cell.find("a:v", ns)
            if inline is not None:
                values.append(inline.text or "")
            elif value_node is not None:
                values.append(value_node.text or "")
            else:
                values.append("")
        rows.append(values)

    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        record = dict(zip(header, row))
        record["UnitPrice"] = float(record["UnitPrice"])
        record["PackSize"] = int(float(record["PackSize"]))
        record["LeadTimeDays"] = int(float(record["LeadTimeDays"]))
        data_rows.append(record)
    return data_rows


def normalize_value(field: str, value):
    if field == "UnitPrice":
        return float(value)
    if field in {"PackSize", "LeadTimeDays"}:
        return int(value)
    return str(value)


def compare_rows(archived_rows, current_rows):
    archived = {row["SKU"]: row for row in archived_rows}
    current = {row["SKU"]: row for row in current_rows}

    result = {
        "discontinued_skus": sorted(sku for sku in archived if sku not in current),
        "modified_skus": [],
    }

    modifications = []
    for sku in sorted(set(archived) & set(current)):
        archived_row = archived[sku]
        current_row = current[sku]
        for field in HEADERS[1:]:
            old_value = normalize_value(field, archived_row[field])
            new_value = normalize_value(field, current_row[field])
            if old_value != new_value:
                modifications.append(
                    {
                        "sku": sku,
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value,
                    }
                )

    result["modified_skus"] = sorted(modifications, key=lambda item: (item["sku"], item["field"]))
    return result


def main():
    archived_rows = read_pdf_rows(PDF_FILE)
    current_rows = read_xlsx_rows(XLSX_FILE)
    result = compare_rows(archived_rows, current_rows)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_vendor_catalog.py
