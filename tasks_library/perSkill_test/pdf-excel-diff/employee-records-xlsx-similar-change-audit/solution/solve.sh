#!/bin/bash
set -euo pipefail

cat > /tmp/solve_employee_diff.py <<'PYTHON'
#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ARCHIVE_FILE = Path(os.environ.get("ARCHIVE_FILE", "/root/employee_records_archive.xlsx"))
CURRENT_FILE = Path(os.environ.get("CURRENT_FILE", "/root/employee_records_current.xlsx"))
OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", "/root/employee_workbook_diff.json"))

MAIN_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

REQUIRED_FIELDS = [
    "Employee ID",
    "Full Name",
    "Department",
    "Location",
    "Salary",
    "Bonus %",
    "Status",
]
NUMERIC_FIELDS = {"Salary", "Bonus %"}


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for char in letters:
        value = value * 26 + (ord(char.upper()) - 64)
    return value


def parse_numeric(raw_value: object) -> int | float:
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        number = float(raw_value)
    else:
        text = str(raw_value).strip().replace(",", "").replace("%", "")
        number = float(text)
    return int(number) if number.is_integer() else number


def normalize_value(field: str, raw_value: object) -> object:
    if field in NUMERIC_FIELDS:
        return parse_numeric(raw_value)
    return str(raw_value).strip()


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> object | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text = cell.find("main:is/main:t", MAIN_NS)
        return text.text if text is not None else ""
    if cell_type == "s":
        value = cell.find("main:v", MAIN_NS)
        if value is None or value.text is None:
            return ""
        return shared_strings[int(value.text)]

    value = cell.find("main:v", MAIN_NS)
    if value is None or value.text is None:
        return None
    text = value.text.strip()
    if text == "":
        return None
    return float(text) if re.search(r"[.eE]", text) else int(text)


def load_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.itertext()) for node in root.findall("main:si", MAIN_NS)]


def read_sheets(path: Path) -> list[tuple[str, list[list[object | None]]]]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = load_shared_strings(workbook)
        workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
        rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))

        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root.findall("rel:Relationship", PKG_REL_NS)
        }

        sheets = []
        for sheet in workbook_root.findall("main:sheets/main:sheet", MAIN_NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rel_map[rel_id]
            xml_path = f"xl/{target.lstrip('/')}"
            sheet_root = ET.fromstring(workbook.read(xml_path))

            parsed_rows = []
            for row in sheet_root.findall("main:sheetData/main:row", MAIN_NS):
                cells = {}
                max_col = 0
                for cell in row.findall("main:c", MAIN_NS):
                    col = column_index(cell.attrib["r"])
                    cells[col] = read_cell_value(cell, shared_strings)
                    max_col = max(max_col, col)
                parsed_row = [None] * max_col
                for col, value in cells.items():
                    parsed_row[col - 1] = value
                parsed_rows.append(parsed_row)
            sheets.append((name, parsed_rows))
        return sheets


def extract_records(path: Path) -> dict[str, dict[str, object]]:
    required = set(REQUIRED_FIELDS)
    for _sheet_name, rows in read_sheets(path):
        header_map = None
        for row in rows:
            normalized = [str(value).strip() for value in row if value is not None and str(value).strip()]
            if required.issubset(set(normalized)):
                header_map = {
                    str(value).strip(): index
                    for index, value in enumerate(row)
                    if value is not None and str(value).strip()
                }
                break
        if header_map is None:
            continue

        records = {}
        header_found = False
        for row in rows:
            normalized = [str(value).strip() for value in row if value is not None and str(value).strip()]
            if not header_found:
                if required.issubset(set(normalized)):
                    header_found = True
                continue

            employee_raw = row[header_map["Employee ID"]] if header_map["Employee ID"] < len(row) else None
            if employee_raw is None or str(employee_raw).strip() == "":
                continue
            employee_id = str(employee_raw).strip()
            if not re.fullmatch(r"EMP\d{5}", employee_id):
                continue

            record = {}
            for field in REQUIRED_FIELDS:
                raw_value = row[header_map[field]] if header_map[field] < len(row) else None
                if raw_value is None or str(raw_value).strip() == "":
                    record[field] = None
                    continue
                record[field] = normalize_value(field, raw_value)
            records[employee_id] = record

        if records:
            return records

    raise RuntimeError(f"Could not find an employee roster in {path}")


def compare_records(archived: dict[str, dict[str, object]], current: dict[str, dict[str, object]]) -> dict[str, object]:
    deleted_employee_ids = sorted(set(archived) - set(current))
    modified_fields = []

    for employee_id in sorted(set(archived) & set(current)):
        old_record = archived[employee_id]
        new_record = current[employee_id]
        for field in sorted(field for field in REQUIRED_FIELDS if field != "Employee ID"):
            old_value = old_record[field]
            new_value = new_record[field]
            if old_value != new_value:
                modified_fields.append(
                    {
                        "employee_id": employee_id,
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value,
                    }
                )

    return {
        "deleted_employee_ids": deleted_employee_ids,
        "modified_fields": modified_fields,
    }


def main() -> None:
    archived_records = extract_records(ARCHIVE_FILE)
    current_records = extract_records(CURRENT_FILE)
    result = compare_records(archived_records, current_records)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PYTHON

python3 /tmp/solve_employee_diff.py
