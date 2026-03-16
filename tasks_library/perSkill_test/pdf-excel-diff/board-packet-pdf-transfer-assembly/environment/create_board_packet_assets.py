#!/usr/bin/env python3

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path("/root")

DOCUMENTS = {
    "agenda_brief.pdf": [
        {
            "marker": "AB-01",
            "title": "Opening Agenda",
            "notes": [
                "Meeting block: Q2 board session",
                "Chair remarks and approval items",
                "Prepared for packet assembly practice",
            ],
        },
        {
            "marker": "AB-02",
            "title": "Board Objectives Summary",
            "notes": [
                "Priority theme: execution discipline",
                "Priority theme: margin recovery",
                "Priority theme: hiring calibration",
            ],
        },
        {
            "marker": "AB-03",
            "title": "Action Log Snapshot",
            "notes": [
                "Open items refreshed before circulation",
                "One-page status summary",
                "Not part of the final packet",
            ],
        },
    ],
    "finance_review.pdf": [
        {
            "marker": "FR-01",
            "title": "Revenue Overview",
            "notes": [
                "Consolidated revenue bridge",
                "Comparative quarter summary",
                "Included without rotation",
            ],
        },
        {
            "marker": "FR-02",
            "title": "Cash Flow Dashboard",
            "notes": [
                "This page is intentionally saved sideways",
                "Final packet must restore upright reading",
                "Use the page-order instructions as the source of truth",
            ],
        },
        {
            "marker": "FR-03",
            "title": "Budget Variance Notes",
            "notes": [
                "Supplemental commentary only",
                "Not part of the requested packet",
                "Retained to force selective extraction",
            ],
        },
    ],
    "product_update.pdf": [
        {
            "marker": "PU-01",
            "title": "Product Roadmap",
            "notes": [
                "Milestone review for the next release",
                "Included near the end of the packet",
                "Portrait source page",
            ],
        },
        {
            "marker": "PU-02",
            "title": "Customer Rollout Risks",
            "notes": [
                "Reference material only",
                "Not included in the final packet",
                "Useful for checking page selection discipline",
            ],
        },
        {
            "marker": "PU-03",
            "title": "Pilot Timeline Review",
            "notes": [
                "This page is intentionally upside down",
                "Final packet must correct the orientation",
                "Keep page content otherwise unchanged",
            ],
        },
    ],
    "governance_appendix.pdf": [
        {
            "marker": "GA-01",
            "title": "Committee Charter Excerpt",
            "notes": [
                "Background reference page",
                "Not requested for the final packet",
                "Included to ensure non-consecutive extraction",
            ],
        },
        {
            "marker": "GA-02",
            "title": "Resolution Digest",
            "notes": [
                "Board consent items summary",
                "Included as a standard upright page",
                "Placed in the middle of the final packet",
            ],
        },
    ],
}

ROTATIONS = {
    "finance_review.pdf": {2: 90},
    "product_update.pdf": {3: 180},
}


def draw_document(pdf_path, pages):
    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    for index, page_spec in enumerate(pages, start=1):
        pdf.setTitle(pdf_path.stem.replace("_", " ").title())
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(72, height - 72, f"Source File: {pdf_path.name}")
        pdf.setFont("Helvetica", 13)
        pdf.drawString(72, height - 108, f"Packet Marker: {page_spec['marker']}")
        pdf.drawString(72, height - 132, f"Page Title: {page_spec['title']}")
        pdf.drawString(72, height - 156, f"Source Page Number: {index}")

        top = height - 204
        for offset, note in enumerate(page_spec["notes"]):
            pdf.drawString(72, top - offset * 22, note)

        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawString(72, 72, "Board packet assembly training asset")
        pdf.showPage()

    pdf.save()


def apply_page_rotations(pdf_path, rotation_map):
    if not rotation_map:
        return

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for index, page in enumerate(reader.pages, start=1):
        if index in rotation_map:
            page.rotate(rotation_map[index])
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def main():
    for filename, page_specs in DOCUMENTS.items():
        destination = ROOT / filename
        draw_document(destination, page_specs)
        apply_page_rotations(destination, ROTATIONS.get(filename, {}))


if __name__ == "__main__":
    main()
