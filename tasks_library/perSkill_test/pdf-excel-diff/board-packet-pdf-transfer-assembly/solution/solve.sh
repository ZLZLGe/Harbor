#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


PLAN_FILE = Path("/root/packet_page_order.txt")
OUTPUT_FILE = Path("/root/board_meeting_packet.pdf")

LINE_RE = re.compile(
    r"^\d+\.\s+"
    r"(?P<pdf>/root/[^\s|]+)\s+\|\s+"
    r"page\s+(?P<page>\d+)"
    r"(?:\s+\|\s+rotate\s+clockwise\s+(?P<rotate>\d+))?$"
)


writer = PdfWriter()

for raw_line in PLAN_FILE.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue

    match = LINE_RE.match(line)
    if not match:
        raise ValueError(f"Unrecognized plan line: {line}")

    pdf_path = Path(match.group("pdf"))
    page_number = int(match.group("page"))
    rotate_degrees = int(match.group("rotate") or 0)

    reader = PdfReader(str(pdf_path))
    page = reader.pages[page_number - 1]
    if rotate_degrees:
        page.rotate(rotate_degrees)
    writer.add_page(page)

with OUTPUT_FILE.open("wb") as handle:
    writer.write(handle)
PY
