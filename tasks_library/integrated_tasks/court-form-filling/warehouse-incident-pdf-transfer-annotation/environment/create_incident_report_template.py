#!/usr/bin/env python3

import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def draw_text_box(pdf, x, y, width, height, label):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y + height + 6, label)
    pdf.rect(x, y, width, height)


def draw_checkbox_group(pdf, label, y, yes_x, no_x, size=18):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(72, y + 5, label)
    pdf.rect(yes_x, y, size, size)
    pdf.drawString(yes_x + size + 6, y + 4, "Yes")
    pdf.rect(no_x, y, size, size)
    pdf.drawString(no_x + size + 6, y + 4, "No")


def main(output_path: str) -> None:
    pdf = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    pdf.setTitle("Warehouse Incident Report")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 42, "Warehouse Incident Report")

    pdf.setLineWidth(1)
    draw_text_box(pdf, 72, 680, 140, 22, "Report Date")
    draw_text_box(pdf, 260, 680, 100, 22, "Report Time")
    draw_text_box(pdf, 72, 630, 210, 22, "Employee Name")
    draw_text_box(pdf, 330, 630, 170, 22, "Job Title")
    draw_text_box(pdf, 72, 580, 140, 22, "Warehouse Zone")
    draw_text_box(pdf, 260, 580, 140, 22, "Incident Date")
    draw_text_box(pdf, 430, 580, 90, 22, "Incident Time")

    draw_checkbox_group(pdf, "Was anyone injured?", 515, 230, 315)
    draw_checkbox_group(pdf, "Was equipment damaged?", 470, 230, 315)
    draw_checkbox_group(pdf, "Was a witness present?", 425, 230, 315)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(72, 392, "Brief Description")
    pdf.rect(72, 280, 468, 100)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(72, 250, "Leave blank: supervisor notes")
    pdf.rect(72, 170, 468, 60)

    pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_incident_report_template.py OUTPUT_PDF")
    main(sys.argv[1])
