#!/bin/bash

set -euo pipefail

cat > /app/workspace/rebuild_audit_packet.py <<'PY'
import csv
from pathlib import Path

from pypdf import PdfReader, PdfWriter


PLAN_PATH = Path("/app/workspace/audit_packet_plan.csv")
SOURCE_DIR = Path("/app/workspace/audit_sources")
OUTPUT_PATH = Path("/app/workspace/audit_review_packet.pdf")


def load_plan():
    with PLAN_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted(rows, key=lambda row: int(row["packet_order"]))


def main():
    writer = PdfWriter()

    for row in load_plan():
        source_path = SOURCE_DIR / row["source_pdf"]
        reader = PdfReader(str(source_path))
        page_index = int(row["page_number"]) - 1
        page = reader.pages[page_index]
        rotation = int(row["rotate_clockwise"]) % 360
        if rotation:
            page.rotate(rotation)
        writer.add_page(page)

    with OUTPUT_PATH.open("wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
PY

python3 /app/workspace/rebuild_audit_packet.py
