#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import re
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_FILE = Path("/root/sales-overview-draft.pptx")
OUTPUT_FILE = Path("/root/results-table-revision.pptx")
WORK_DIR = Path(tempfile.mkdtemp(prefix="sales_table_revision_"))
SLIDE_XML = WORK_DIR / "ppt/slides/slide1.xml"
UNPACK_SCRIPT = Path("/root/.codex/skills/pptx/ooxml/scripts/unpack.py")
PACK_SCRIPT = Path("/root/.codex/skills/pptx/ooxml/scripts/pack.py")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
ET.register_namespace("a", NS["a"])
ET.register_namespace("p", NS["p"])
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")


def shape_text(shape):
    texts = []
    for paragraph in shape.findall(".//a:p", NS):
        line = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).strip()
        if line:
            texts.append(line)
    return texts


def cell_text(cell):
    return "".join(node.text or "" for node in cell.findall(".//a:t", NS)).strip()


def set_cell_text(cell, value):
    text_nodes = cell.findall(".//a:t", NS)
    if not text_nodes:
        raise ValueError("Target cell does not contain any text node")
    text_nodes[0].text = value
    for extra in text_nodes[1:]:
        extra.text = ""


def parse_memo(root):
    for shape in root.findall(".//p:sp", NS):
        lines = shape_text(shape)
        if lines and lines[0] == "Revision memo":
            updates = {}
            revised_date = None
            for line in lines[1:]:
                match = re.fullmatch(r"(.+?)\s*/\s*(.+?)\s*=\s*([0-9]+(?:\.[0-9]+)?)", line)
                if match:
                    row_label, col_label, new_value = match.groups()
                    updates[(row_label, col_label)] = new_value
                    continue
                match = re.fullmatch(r"Last revised:\s*(\d{4}-\d{2}-\d{2})", line)
                if match:
                    revised_date = match.group(1)
            if not updates or revised_date is None:
                raise ValueError("Revision memo is missing updates or revised date")
            return updates, revised_date
    raise ValueError("Revision memo text box not found")


def update_table(root, updates):
    table = root.find(".//a:tbl", NS)
    if table is None:
        raise ValueError("Native table not found on slide")

    rows = table.findall("a:tr", NS)
    header_cells = rows[0].findall("a:tc", NS)
    col_index = {cell_text(cell): idx for idx, cell in enumerate(header_cells)}
    row_index = {}
    for idx, row in enumerate(rows[1:], start=1):
        first_cell = row.find("a:tc", NS)
        row_index[cell_text(first_cell)] = idx

    for (row_label, col_label), new_value in updates.items():
        target_row = row_index[row_label]
        target_col = col_index[col_label]
        target_cell = rows[target_row].findall("a:tc", NS)[target_col]
        set_cell_text(target_cell, new_value)


def update_footer(root, revised_date):
    for shape in root.findall(".//p:sp", NS):
        lines = shape_text(shape)
        if len(lines) == 1 and lines[0].startswith("Last revised:"):
            text_nodes = shape.findall(".//a:t", NS)
            if not text_nodes:
                raise ValueError("Footer text node is missing")
            text_nodes[0].text = f"Last revised: {revised_date}"
            for extra in text_nodes[1:]:
                extra.text = ""
            return
    raise ValueError("Footer text box not found")


subprocess.run(["python3", str(UNPACK_SCRIPT), str(INPUT_FILE), str(WORK_DIR)], check=True)

tree = ET.parse(SLIDE_XML)
root = tree.getroot()
updates, revised_date = parse_memo(root)
update_table(root, updates)
update_footer(root, revised_date)
tree.write(SLIDE_XML, encoding="UTF-8", xml_declaration=True)

subprocess.run(
    ["python3", str(PACK_SCRIPT), str(WORK_DIR), str(OUTPUT_FILE), "--force"],
    check=True,
)
PY
