#!/bin/bash
set -euo pipefail

cat > /tmp/solve_warehouse_pdf.py <<'PY'
#!/usr/bin/env python3

import io
import re

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


INPUT_PDF = "/root/warehouse-inspection-checklist.pdf"
INPUT_RECORD = "/root/inspection-record.md"
OUTPUT_PDF = "/root/warehouse-inspection-completed.pdf"

PAGE_WIDTH, PAGE_HEIGHT = letter
CHECKBOX_SIZE = 14

HEADER_FIELDS = {
    "Facility": (100, 712),
    "Inspection date": (452, 712),
    "Shift": (76, 682),
    "Inspector": (248, 682),
    "Area": (76, 652),
}

ROW_Y = {
    "Loading dock doors close and latch properly": 543,
    "Forklift charging aisle remains clear": 505,
    "Spill kit supplies are stocked": 467,
    "Cold storage thermometer within range": 429,
    "Emergency exit lights operational": 391,
}

PASS_X = 432
ACTION_X = 502

FOLLOW_UP_BOXES = {
    "Follow-up needed": {"yes": (150, 343), "no": (215, 343)},
    "Immediate hazard isolated": {"yes": (454, 343), "no": (520, 343)},
    "Reinspection required": {"yes": (158, 209), "no": (223, 209)},
}

PAGE_TWO_TEXT = {
    "Issue observed": (48, 676, 500),
    "Corrective action taken": (48, 516, 500),
    "Outstanding follow-up": (48, 386, 500),
}

PAGE_TWO_FIELDS = {
    "Maintenance ticket": (136, 294),
    "Supervisor notified at": (408, 294),
    "Completion deadline": (150, 254),
    "Supervisor initials": (442, 254),
    "Inspector signature": (146, 169),
}


def parse_record(path):
    data = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("- ") or ":" not in line:
                continue
            key, value = line[2:].split(":", 1)
            data[key.strip()] = value.strip()
    return data


def draw_mark(pdf, x, y, size=CHECKBOX_SIZE):
    pdf.setLineWidth(1.6)
    pdf.line(x + 3, y + 3, x + size - 3, y + size - 3)
    pdf.line(x + 3, y + size - 3, x + size - 3, y + 3)


def draw_wrapped_text(pdf, x, top_y, width, text, leading=13, font_size=10):
    pdf.setFont("Helvetica", font_size)
    words = text.split()
    current = ""
    lines = []
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if pdf.stringWidth(candidate, "Helvetica", font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = top_y
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading


def build_overlay(data):
    overlay_stream = io.BytesIO()
    pdf = canvas.Canvas(overlay_stream, pagesize=letter)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(*HEADER_FIELDS["Facility"], data["Facility"])
    pdf.drawString(*HEADER_FIELDS["Inspection date"], data["Inspection date"])
    pdf.drawString(*HEADER_FIELDS["Shift"], data["Shift"])
    pdf.drawString(*HEADER_FIELDS["Inspector"], data["Inspector"])
    pdf.drawString(*HEADER_FIELDS["Area"], data["Area"])

    for label, row_y in ROW_Y.items():
        status = data[label].lower()
        x = PASS_X if status == "pass" else ACTION_X
        draw_mark(pdf, x, row_y)

    for field_name in ("Follow-up needed", "Immediate hazard isolated"):
        value = data[field_name].lower()
        draw_mark(pdf, *FOLLOW_UP_BOXES[field_name][value])

    pdf.showPage()
    pdf.setFont("Helvetica", 10)
    draw_wrapped_text(pdf, PAGE_TWO_TEXT["Issue observed"][0], PAGE_TWO_TEXT["Issue observed"][1], PAGE_TWO_TEXT["Issue observed"][2], data["Issue observed"])
    draw_wrapped_text(pdf, PAGE_TWO_TEXT["Corrective action taken"][0], PAGE_TWO_TEXT["Corrective action taken"][1], PAGE_TWO_TEXT["Corrective action taken"][2], data["Corrective action taken"])
    draw_wrapped_text(pdf, PAGE_TWO_TEXT["Outstanding follow-up"][0], PAGE_TWO_TEXT["Outstanding follow-up"][1], PAGE_TWO_TEXT["Outstanding follow-up"][2], data["Outstanding follow-up"])

    pdf.drawString(*PAGE_TWO_FIELDS["Maintenance ticket"], data["Maintenance ticket"])
    pdf.drawString(*PAGE_TWO_FIELDS["Supervisor notified at"], data["Supervisor notified at"])
    pdf.drawString(*PAGE_TWO_FIELDS["Completion deadline"], data["Completion deadline"])
    pdf.drawString(*PAGE_TWO_FIELDS["Supervisor initials"], data["Supervisor initials"])
    pdf.drawString(*PAGE_TWO_FIELDS["Inspector signature"], data["Inspector"])

    draw_mark(pdf, *FOLLOW_UP_BOXES["Reinspection required"][data["Reinspection required"].lower()])

    pdf.save()
    overlay_stream.seek(0)
    return overlay_stream


def merge_pdfs(base_path, overlay_stream, output_path):
    base_reader = PdfReader(base_path)
    overlay_reader = PdfReader(overlay_stream)
    writer = PdfWriter()

    for base_page, overlay_page in zip(base_reader.pages, overlay_reader.pages):
        base_page.merge_page(overlay_page)
        writer.add_page(base_page)

    with open(output_path, "wb") as handle:
        writer.write(handle)


def main():
    data = parse_record(INPUT_RECORD)
    overlay_stream = build_overlay(data)
    merge_pdfs(INPUT_PDF, overlay_stream, OUTPUT_PDF)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_warehouse_pdf.py
