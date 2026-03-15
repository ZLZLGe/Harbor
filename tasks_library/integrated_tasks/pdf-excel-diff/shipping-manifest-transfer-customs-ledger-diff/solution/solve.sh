#!/bin/bash
set -euo pipefail

cat > /tmp/solve_shipping_manifest.py <<'PY'
#!/usr/bin/env python3

import json
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

PDF_FILE = Path("/root/export_manifest_packet.pdf")
XLSX_FILE = Path("/root/customs_ledger.xlsx")
OUTPUT_FILE = Path("/root/shipping_manifest_variances.json")

PDF_HEADERS = [
    "manifest_id",
    "line_no",
    "item_code",
    "destination_port",
    "carton_count",
    "gross_weight_kg",
    "declared_value_usd",
]
COMPARE_FIELDS = [
    "destination_port",
    "carton_count",
    "gross_weight_kg",
    "declared_value_usd",
]
NUMERIC_INT_FIELDS = {"line_no", "carton_count"}
NUMERIC_FLOAT_FIELDS = {"gross_weight_kg", "declared_value_usd"}


def decode_pdf_literal(value: str) -> str:
    return value.replace(r"\\", "\\").replace(r"\(", "(").replace(r"\)", ")")


def normalize_field(field: str, value: str):
    if field in NUMERIC_INT_FIELDS:
        return int(float(value))
    if field in NUMERIC_FLOAT_FIELDS:
        return float(value)
    return str(value)


def parse_pdf_manifest(path: Path):
    raw_text = path.read_bytes().decode("latin-1", errors="ignore")
    literals = [
        decode_pdf_literal(match)
        for match in re.findall(r"\((.*?)\)\s*Tj", raw_text, flags=re.DOTALL)
    ]

    manifest = {}
    for line in literals:
        if not line.startswith("MNF-"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != len(PDF_HEADERS):
            continue
        row = {}
        for field, value in zip(PDF_HEADERS, parts):
            row[field] = normalize_field(field, value)
        manifest[(row["manifest_id"], row["line_no"])] = row
    return manifest


def load_sheet_map(zf: zipfile.ZipFile):
    ns_main = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rel_map = {}
    for rel in rels_root:
        rel_map[rel.attrib["Id"]] = f'xl/{rel.attrib["Target"]}'

    sheet_map = {}
    for sheet in workbook_root.findall("a:sheets/a:sheet", ns_main):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        sheet_map[name] = rel_map[rel_id]
    return sheet_map


def cell_value(cell, ns):
    inline = cell.find("a:is/a:t", ns)
    if inline is not None:
        return inline.text or ""
    value_node = cell.find("a:v", ns)
    if value_node is not None:
        return value_node.text or ""
    return ""


def read_sheet_rows(zf: zipfile.ZipFile, sheet_path: str):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(zf.read(sheet_path))
    rows = []
    for row in root.findall(".//a:sheetData/a:row", ns):
        values = [cell_value(cell, ns) for cell in row.findall("a:c", ns)]
        rows.append(values)
    return rows


def parse_workbook(path: Path):
    with zipfile.ZipFile(path) as zf:
        sheet_map = load_sheet_map(zf)
        rows = read_sheet_rows(zf, sheet_map["CurrentLedger"])

    header = rows[0]
    workbook_rows = []
    for values in rows[1:]:
        row = {}
        for field, value in zip(header, values):
            row[field] = normalize_field(field, value)
        workbook_rows.append(row)
    return workbook_rows


def compare_rows(old_rows, current_rows):
    current_map = {
        (row["manifest_id"], row["line_no"]): row
        for row in current_rows
    }

    missing = []
    changed = []
    for key in sorted(old_rows):
        old_row = old_rows[key]
        new_row = current_map.get(key)
        if new_row is None:
            missing.append(
                {
                    "manifest_id": old_row["manifest_id"],
                    "line_no": old_row["line_no"],
                }
            )
            continue

        for field in COMPARE_FIELDS:
            if old_row[field] != new_row[field]:
                changed.append(
                    {
                        "manifest_id": old_row["manifest_id"],
                        "line_no": old_row["line_no"],
                        "field": field,
                        "old_value": old_row[field],
                        "new_value": new_row[field],
                    }
                )

    changed.sort(key=lambda item: (item["manifest_id"], item["line_no"], item["field"]))
    return {
        "missing_line_items": missing,
        "changed_line_items": changed,
    }


def main():
    old_rows = parse_pdf_manifest(PDF_FILE)
    current_rows = parse_workbook(XLSX_FILE)
    result = compare_rows(old_rows, current_rows)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_shipping_manifest.py
