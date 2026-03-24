#!/usr/bin/env python3

import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = letter
CHECKBOX_SIZE = 14

ROW_LABELS = [
    "Loading dock doors close and latch properly",
    "Forklift charging aisle remains clear",
    "Spill kit supplies are stocked",
    "Cold storage thermometer within range",
    "Emergency exit lights operational",
]

ROW_Y = [543, 505, 467, 429, 391]
PASS_X = 432
ACTION_X = 502


def draw_box(pdf, x, y, size=CHECKBOX_SIZE):
    pdf.rect(x, y, size, size, stroke=1, fill=0)


def draw_line_field(pdf, x1, x2, y):
    pdf.line(x1, y, x2, y)


def build_page_one(pdf):
    pdf.setTitle("Warehouse Inspection Checklist")
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(40, 754, "Warehouse Safety and Sanitation Inspection Checklist")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 739, "Complete all observed items. Mark exactly one status box per line.")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 711, "Facility")
    draw_line_field(pdf, 96, 340, 708)
    pdf.drawString(355, 711, "Inspection date")
    draw_line_field(pdf, 450, 560, 708)

    pdf.drawString(40, 681, "Shift")
    draw_line_field(pdf, 72, 170, 678)
    pdf.drawString(190, 681, "Inspector")
    draw_line_field(pdf, 244, 420, 678)

    pdf.drawString(40, 651, "Area")
    draw_line_field(pdf, 72, 560, 648)
    pdf.drawString(40, 621, "Weather / conditions")
    draw_line_field(pdf, 145, 560, 618)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, 583, "Inspection item")
    pdf.drawString(PASS_X - 4, 583, "PASS")
    pdf.drawString(ACTION_X - 7, 583, "ACTION")

    pdf.line(40, 575, 560, 575)

    pdf.setFont("Helvetica", 10)
    for label, row_y in zip(ROW_LABELS, ROW_Y):
        pdf.drawString(46, row_y + 4, label)
        draw_box(pdf, PASS_X, row_y)
        draw_box(pdf, ACTION_X, row_y)
        pdf.line(40, row_y - 12, 560, row_y - 12)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 348, "Follow-up needed")
    draw_box(pdf, 150, 343)
    pdf.drawString(170, 347, "Yes")
    draw_box(pdf, 215, 343)
    pdf.drawString(235, 347, "No")

    pdf.drawString(300, 348, "Immediate hazard isolated")
    draw_box(pdf, 454, 343)
    pdf.drawString(474, 347, "Yes")
    draw_box(pdf, 520, 343)
    pdf.drawString(540, 347, "No")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, 300, "Inspector notes continue on page 2.")


def draw_text_block(pdf, x, top_y, width, text, leading=13, font_size=10):
    pdf.setFont("Helvetica", font_size)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if pdf.stringWidth(candidate, "Helvetica", font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    cursor_y = top_y
    for line in lines:
        pdf.drawString(x, cursor_y, line)
        cursor_y -= leading


def build_page_two(pdf):
    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 754, "Warehouse Inspection Follow-up")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 739, "Record only the observed issues and the actions that were actually taken.")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, 706, "Observed issue")
    pdf.rect(40, 584, 520, 108, stroke=1, fill=0)

    pdf.drawString(40, 546, "Corrective action taken")
    pdf.rect(40, 454, 520, 74, stroke=1, fill=0)

    pdf.drawString(40, 416, "Outstanding follow-up")
    pdf.rect(40, 344, 520, 74, stroke=1, fill=0)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 294, "Maintenance ticket")
    draw_line_field(pdf, 132, 240, 291)
    pdf.drawString(290, 294, "Supervisor notified at")
    draw_line_field(pdf, 405, 560, 291)

    pdf.drawString(40, 254, "Completion deadline")
    draw_line_field(pdf, 146, 290, 251)
    pdf.drawString(330, 254, "Supervisor initials")
    draw_line_field(pdf, 438, 520, 251)

    pdf.drawString(40, 214, "Reinspection required")
    draw_box(pdf, 158, 209)
    pdf.drawString(178, 213, "Yes")
    draw_box(pdf, 223, 209)
    pdf.drawString(243, 213, "No")

    pdf.drawString(40, 169, "Inspector signature")
    draw_line_field(pdf, 142, 330, 166)
    pdf.drawString(350, 169, "Manager review initials")
    draw_line_field(pdf, 476, 560, 166)

    pdf.drawString(40, 129, "Next audit date")
    draw_line_field(pdf, 116, 250, 126)


def build_form(output_path):
    pdf = canvas.Canvas(output_path, pagesize=letter)
    build_page_one(pdf)
    build_page_two(pdf)
    pdf.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_warehouse_checklist.py OUTPUT_PDF")
    build_form(sys.argv[1])
