#!/bin/bash
set -euo pipefail

cat > /tmp/annotate_incident_report.py <<'PYTHON'
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

INPUT_PDF = "/root/warehouse-incident-report.pdf"
OUTPUT_PDF = "/root/incident-report-completed.pdf"

VALUES = {
    "report_date": "2026-02-14",
    "report_time": "08:10",
    "employee_name": "Daniel Ruiz",
    "job_title": "Forklift Operator",
    "warehouse_zone": "Zone 3",
    "incident_date": "2026-02-14",
    "incident_time": "07:35",
    "description": "Backing pallet jack clipped rack B-17; shelf beam bent; area cordoned off for inspection.",
}

CHECKED_BOXES = [
    (315, 515, 18),
    (230, 470, 18),
    (230, 425, 18),
]


def draw_x(pdf, x, y, size):
    inset = 3
    pdf.setLineWidth(2)
    pdf.line(x + inset, y + inset, x + size - inset, y + size - inset)
    pdf.line(x + inset, y + size - inset, x + size - inset, y + inset)


def build_overlay() -> PdfReader:
    packet = BytesIO()
    pdf = canvas.Canvas(packet, pagesize=letter)
    pdf.setFont("Helvetica", 11)

    pdf.drawString(78, 688, VALUES["report_date"])
    pdf.drawString(266, 688, VALUES["report_time"])
    pdf.drawString(78, 638, VALUES["employee_name"])
    pdf.drawString(336, 638, VALUES["job_title"])
    pdf.drawString(78, 588, VALUES["warehouse_zone"])
    pdf.drawString(266, 588, VALUES["incident_date"])
    pdf.drawString(436, 588, VALUES["incident_time"])

    text = pdf.beginText(78, 364)
    text.setFont("Helvetica", 11)
    text.textLine(VALUES["description"])
    pdf.drawText(text)

    for box in CHECKED_BOXES:
        draw_x(pdf, *box)

    pdf.save()
    packet.seek(0)
    return PdfReader(packet)


def main() -> None:
    base_reader = PdfReader(INPUT_PDF)
    overlay_reader = build_overlay()
    writer = PdfWriter()

    page = base_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)

    with open(OUTPUT_PDF, "wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
PYTHON

python3 /tmp/annotate_incident_report.py
