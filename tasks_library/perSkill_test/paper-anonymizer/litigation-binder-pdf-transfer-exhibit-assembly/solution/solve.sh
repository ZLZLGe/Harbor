#!/bin/bash
set -euo pipefail

mkdir -p /root/output /tmp/binder_parts

python3 - <<'PY'
from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter


INPUT_DIR = Path("/root/case_files")
OUTPUT_FILE = Path("/root/output/exhibit_binder.pdf")
TEMP_DIR = Path("/tmp/binder_parts")
BINDER_TITLE = "Exhibit Binder"

COVER_LINES = [
    "Exhibit Binder",
    "Case: Alder Ridge v. North Basin Logistics",
    "Section 1: Exhibit A - Operations Memo",
    "Section 2: Exhibit B - Email Chain",
    "Section 3: Exhibit C - Billing Backup",
]

EXHIBITS = [
    {
        "label": "Exhibit A - Operations Memo",
        "filename": "exhibit_a_operations_memo.pdf",
        "pages": [2, 3, 4],
    },
    {
        "label": "Exhibit B - Email Chain",
        "filename": "exhibit_b_email_chain.pdf",
        "pages": [1, 2, 5],
    },
    {
        "label": "Exhibit C - Billing Backup",
        "filename": "exhibit_c_billing_backup.pdf",
        "pages": [3, 4, 5, 6],
    },
]


def write_cover_page(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    title_rect = fitz.Rect(72, 72, 540, 140)
    page.insert_textbox(title_rect, COVER_LINES[0], fontsize=26, align=1)
    y = 180
    for line in COVER_LINES[1:]:
        rect = fitz.Rect(72, y, 540, y + 36)
        page.insert_textbox(rect, line, fontsize=18, align=0)
        y += 42
    doc.save(path)
    doc.close()


def write_divider_page(path: Path, label: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    rect = fitz.Rect(72, 280, 540, 380)
    page.insert_textbox(rect, label, fontsize=28, align=1)
    doc.save(path)
    doc.close()


def add_pdf_pages(writer: PdfWriter, pdf_path: Path, readers: list[PdfReader]) -> None:
    reader = PdfReader(str(pdf_path))
    readers.append(reader)
    for page in reader.pages:
        writer.add_page(page)


writer = PdfWriter()
live_readers: list[PdfReader] = []

cover_path = TEMP_DIR / "cover.pdf"
write_cover_page(cover_path)
add_pdf_pages(writer, cover_path, live_readers)

for exhibit in EXHIBITS:
    divider_path = TEMP_DIR / f"{exhibit['filename']}.divider.pdf"
    write_divider_page(divider_path, exhibit["label"])
    add_pdf_pages(writer, divider_path, live_readers)

    reader = PdfReader(str(INPUT_DIR / exhibit["filename"]))
    live_readers.append(reader)
    for page_number in exhibit["pages"]:
        page = reader.pages[page_number - 1]
        if page.rotation:
            page.transfer_rotation_to_content()
        writer.add_page(page)

writer.add_metadata({"/Title": BINDER_TITLE})
with OUTPUT_FILE.open("wb") as handle:
    writer.write(handle)
PY
