#!/bin/bash
set -e

python3 <<'PY'
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path("/root")
manifest = json.loads((ROOT / "board_packet_manifest.json").read_text())
writer = PdfWriter()


def make_text_page(output_path: Path, lines: list[str]) -> None:
    page_width, page_height = letter
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    y = page_height - 150
    for index, line in enumerate(lines):
        if index == 0:
            font_name, font_size = "Helvetica-Bold", 24
        elif index == 1:
            font_name, font_size = "Helvetica-Bold", 18
        elif line == manifest["confidentiality_label"]:
            font_name, font_size = "Helvetica-Oblique", 12
        else:
            font_name, font_size = "Helvetica", 14
        pdf.setFont(font_name, font_size)
        pdf.drawCentredString(page_width / 2, y, line)
        y -= 38 if index == 0 else 28
    pdf.save()


cover_lines = [
    manifest["book_title"],
    manifest["meeting_title"],
    f'Meeting Date: {manifest["meeting_date"]}',
    f'Meeting Time: {manifest["meeting_time"]}',
    f'Location: {manifest["meeting_location"]}',
    manifest["confidentiality_label"],
]
cover_path = Path("/tmp/board_book_cover.pdf")
make_text_page(cover_path, cover_lines)
writer.add_page(PdfReader(str(cover_path)).pages[0])

for section in manifest["sections"]:
    divider_path = Path(f'/tmp/board_book_divider_{section["section_code"]}.pdf')
    divider_lines = [
        f'Section {section["section_code"]}',
        section["section_title"],
        manifest["confidentiality_label"],
    ]
    make_text_page(divider_path, divider_lines)
    writer.add_page(PdfReader(str(divider_path)).pages[0])

    for item in section["items"]:
        source_reader = PdfReader(str(ROOT / item["file"]))
        for page_number in item["pages"]:
            writer.add_page(source_reader.pages[page_number - 1])

with open(ROOT / "board_book.pdf", "wb") as fh:
    writer.write(fh)
PY
