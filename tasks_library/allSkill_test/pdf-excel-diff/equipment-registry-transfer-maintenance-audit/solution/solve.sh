#!/bin/bash
set -euo pipefail

cat > /tmp/solve_equipment_registry.py <<'PY'
#!/usr/bin/env python3

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

PDF_FILE = Path("/root/equipment_inspection_report.pdf")
XLSX_FILE = Path("/root/equipment_registry.xlsx")
OUTPUT_FILE = Path("/root/equipment_registry_changes.json")

HEADERS = [
    "asset_tag",
    "equipment_name",
    "location",
    "next_inspection_date",
    "service_vendor",
    "risk_level",
    "inspection_interval_days",
]
TRACKED_FIELDS = [
    "inspection_interval_days",
    "next_inspection_date",
    "risk_level",
    "service_vendor",
]
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def decode_pdf_literal(value: str) -> str:
    return value.replace(r"\\", "\\").replace(r"\(", "(").replace(r"\)", ")")


def normalize_date(value: str) -> str:
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value!r}")


def normalize_value(field: str, value):
    if field == "next_inspection_date":
        return normalize_date(value)
    if field == "inspection_interval_days":
        return int(str(value).strip())
    return str(value).strip()


def read_pdf_rows(path: Path):
    raw_text = path.read_bytes().decode("latin-1", errors="ignore")
    literals = [
        decode_pdf_literal(match)
        for match in re.findall(r"\((.*?)\)\s*Tj", raw_text, flags=re.DOTALL)
    ]

    rows = []
    for line in literals:
        if not line.startswith("EQ-"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != len(HEADERS):
            continue
        record = dict(zip(HEADERS, parts))
        record["next_inspection_date"] = normalize_date(record["next_inspection_date"])
        record["inspection_interval_days"] = int(record["inspection_interval_days"])
        rows.append(record)
    return rows


def cell_value(cell, ns):
    inline = cell.find("a:is", ns)
    if inline is not None:
        return "".join(inline.itertext())
    value_node = cell.find("a:v", ns)
    return "" if value_node is None else (value_node.text or "")


def read_xlsx_rows(path: Path):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        xml_data = zf.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(xml_data)
    rows = []
    for row_node in root.findall(".//a:sheetData/a:row", ns):
        values = [cell_value(cell, ns).strip() for cell in row_node.findall("a:c", ns)]
        rows.append(values)

    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        record = dict(zip(header, row))
        record["next_inspection_date"] = normalize_date(record["next_inspection_date"])
        record["inspection_interval_days"] = int(record["inspection_interval_days"])
        data_rows.append(record)
    return data_rows


def compare_rows(archived_rows, current_rows):
    archived = {row["asset_tag"]: row for row in archived_rows}
    current = {row["asset_tag"]: row for row in current_rows}

    retired = sorted(tag for tag in archived if tag not in current)
    updates = []

    for asset_tag in sorted(set(archived) & set(current)):
        old_row = archived[asset_tag]
        new_row = current[asset_tag]
        for field in TRACKED_FIELDS:
            old_value = normalize_value(field, old_row[field])
            new_value = normalize_value(field, new_row[field])
            if old_value != new_value:
                updates.append(
                    {
                        "asset_tag": asset_tag,
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value,
                    }
                )

    return {
        "retired_equipment": retired,
        "updated_records": sorted(updates, key=lambda item: (item["asset_tag"], item["field"])),
    }


def main():
    archived_rows = read_pdf_rows(PDF_FILE)
    current_rows = read_xlsx_rows(XLSX_FILE)
    result = compare_rows(archived_rows, current_rows)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_equipment_registry.py
