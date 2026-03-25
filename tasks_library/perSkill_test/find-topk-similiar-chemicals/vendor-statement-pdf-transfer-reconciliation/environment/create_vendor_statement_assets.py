#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def draw_page(pdf: canvas.Canvas, lines: list[str], page_number: int, total_pages: int) -> None:
    width, height = letter
    y = height - 54

    pdf.setFont("Courier-Bold", 11)
    pdf.drawString(54, y, f"Vendor Statement Batch B7  |  Page {page_number} of {total_pages}")
    y -= 18

    pdf.setFont("Courier", 9)
    pdf.drawString(54, y, "Prepared for AP close: 2026-02-20")
    y -= 22

    pdf.setFont("Courier", 10)
    for line in lines:
        pdf.drawString(54, y, line)
        y -= 14

    pdf.setFont("Courier-Oblique", 8)
    pdf.drawString(54, 30, "Footer note: section subtotals are informational only.")


def main(seed_path: str, output_path: str) -> None:
    pages = json.loads(Path(seed_path).read_text(encoding="utf-8"))["pages"]
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(out_path), pagesize=letter)
    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        draw_page(pdf, page["lines"], index, total_pages)
        pdf.showPage()

    pdf.save()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
