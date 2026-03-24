#!/bin/bash
set -euo pipefail

INPUT_PPTX="${INPUT_PPTX:-/root/sales-forecast-deck.pptx}"
OUTPUT_PPTX="${OUTPUT_PPTX:-/root/revenue-forecast-refresh.pptx}"

cat > /tmp/refresh_forecast.py <<'PY'
#!/usr/bin/env python3
import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path(__import__("os").environ.get("INPUT_PPTX", "/root/sales-forecast-deck.pptx"))
OUTPUT_PPTX = Path(__import__("os").environ.get("OUTPUT_PPTX", "/root/revenue-forecast-refresh.pptx"))

PPT_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def column_letters(cell_ref: str) -> str:
    return "".join(ch for ch in cell_ref if ch.isalpha())


def row_number(cell_ref: str) -> int:
    return int("".join(ch for ch in cell_ref if ch.isdigit()))


def parse_slide_updates(pptx_path: Path):
    updates = {}
    with zipfile.ZipFile(pptx_path, "r") as zf:
        slide_names = sorted(
            name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        for slide_name in slide_names:
            root = ET.fromstring(zf.read(slide_name))
            for shape in root.findall(".//p:sp", PPT_NS):
                text = "".join(node.text or "" for node in shape.findall(".//a:t", PPT_NS))
                for region, quarter, value in re.findall(r"([A-Za-z]+)\s+Q([1-4])\s*=\s*([0-9]+(?:\.[0-9]+)?)", text):
                    updates[(region, f"Q{quarter}")] = float(value)
    if not updates:
        raise ValueError("No forecast updates found in slide text.")
    return updates


def load_shared_strings(xlsx_zip: zipfile.ZipFile):
    root = ET.fromstring(xlsx_zip.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("x:si", XLSX_NS):
        text = "".join(node.text or "" for node in item.findall(".//x:t", XLSX_NS))
        values.append(text)
    return values


def get_cell_value(cell, shared_strings):
    value_node = cell.find("x:v", XLSX_NS)
    if value_node is None:
        return None
    raw = value_node.text or ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw)]
    return float(raw)


def set_numeric_value(cell, value):
    value_node = cell.find("x:v", XLSX_NS)
    if value_node is None:
        value_node = ET.SubElement(cell, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    value_node.text = f"{value:.1f}"


def refresh_embedded_workbook(xlsx_bytes: bytes, updates):
    source = BytesIO(xlsx_bytes)
    output = BytesIO()
    with zipfile.ZipFile(source, "r") as zin:
        shared_strings = load_shared_strings(zin)
        sheet_root = ET.fromstring(zin.read("xl/worksheets/sheet1.xml"))
        cells = {cell.attrib["r"]: cell for cell in sheet_root.findall(".//x:c", XLSX_NS)}

        quarter_columns = {}
        region_rows = {}
        total_row = None

        for ref, cell in cells.items():
            col = column_letters(ref)
            row = row_number(ref)
            value = get_cell_value(cell, shared_strings)
            if row == 1 and col != "A":
                quarter_columns[str(value)] = col
            elif col == "A" and row > 1:
                region_rows[str(value)] = row
                if str(value) == "Company Total":
                    total_row = row

        if total_row is None:
            raise ValueError("Could not find the total row in the embedded workbook.")

        for (region, quarter), value in updates.items():
            cell_ref = f"{quarter_columns[quarter]}{region_rows[region]}"
            set_numeric_value(cells[cell_ref], value)

        for quarter, col in quarter_columns.items():
            total = 0.0
            for region, row in region_rows.items():
                if row == total_row:
                    continue
                total += float(get_cell_value(cells[f"{col}{row}"], shared_strings))
            set_numeric_value(cells[f"{col}{total_row}"], total)

        new_sheet = ET.tostring(sheet_root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "xl/worksheets/sheet1.xml":
                    data = new_sheet
                zout.writestr(item, data)
    return output.getvalue()


def find_embedded_workbook_path(pptx_path: Path):
    with zipfile.ZipFile(pptx_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("ppt/embeddings/") and name.endswith(".xlsx"):
                return name
    raise ValueError("No embedded workbook found in the presentation.")


def write_updated_pptx(input_path: Path, output_path: Path, workbook_path: str, workbook_bytes: bytes):
    with zipfile.ZipFile(input_path, "r") as zin, zipfile.ZipFile(output_path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == workbook_path:
                data = workbook_bytes
            zout.writestr(item, data)


def main():
    updates = parse_slide_updates(INPUT_PPTX)
    workbook_path = find_embedded_workbook_path(INPUT_PPTX)
    with zipfile.ZipFile(INPUT_PPTX, "r") as zf:
        workbook_bytes = zf.read(workbook_path)
    refreshed = refresh_embedded_workbook(workbook_bytes, updates)
    write_updated_pptx(INPUT_PPTX, OUTPUT_PPTX, workbook_path, refreshed)


if __name__ == "__main__":
    main()
PY

python3 /tmp/refresh_forecast.py
