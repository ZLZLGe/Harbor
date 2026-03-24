#!/bin/bash

set -euo pipefail

mkdir -p /app/artifacts

python3 - <<'PY'
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


INPUT_DIR = Path("/app/workspace/input")
ARTIFACT_DIR = Path("/app/artifacts")
MANIFEST_PATH = INPUT_DIR / "submission_manifest.json"
OUTPUT_PATH = ARTIFACT_DIR / "regulatory_submission_packet.pdf"
COVER_PATH = ARTIFACT_DIR / "_cover_page.pdf"


def build_cover(manifest, output_path):
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    y = height - 72

    c.setTitle(manifest["output_title"])
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, y, manifest["packet_title"])
    y -= 36

    c.setFont("Helvetica", 12)
    cover_fields = [
        ("Packet title", manifest["packet_title"]),
        ("Packet ID", manifest["packet_id"]),
        ("Applicant", manifest["applicant"]),
        ("Facility", manifest["facility"]),
        ("Permit number", manifest["permit_number"]),
        ("Submission deadline", manifest["submission_deadline"]),
        ("Prepared by", manifest["prepared_by"]),
    ]
    for label, value in cover_fields:
        c.drawString(72, y, f"{label}: {value}")
        y -= 20

    y -= 8
    c.setFont("Helvetica-Bold", 13)
    c.drawString(72, y, "Included exhibits")
    y -= 24

    c.setFont("Helvetica", 12)
    for item in manifest["assembly_order"]:
        c.drawString(90, y, f"{item['section_code']}. {item['section_title']}")
        y -= 18

    c.save()


def assemble_packet(manifest):
    build_cover(manifest, COVER_PATH)

    writer = PdfWriter()
    writer.add_metadata(
        {
            "/Title": manifest["output_title"],
            "/Author": manifest["prepared_by"],
            "/Subject": manifest["packet_id"],
        }
    )

    cover_reader = PdfReader(str(COVER_PATH))
    writer.add_page(cover_reader.pages[0])

    for item in manifest["assembly_order"]:
        source_path = INPUT_DIR / item["source_pdf"]
        source_reader = PdfReader(str(source_path))
        page = source_reader.pages[item["page_number"] - 1]
        rotation = int(item.get("rotation_correction_clockwise", 0))
        if rotation:
            page.rotate(rotation)
        writer.add_page(page)

    with OUTPUT_PATH.open("wb") as handle:
        writer.write(handle)


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assemble_packet(manifest)


if __name__ == "__main__":
    main()
PY
