#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pypdf import PdfReader, PdfWriter

INPUT_PDF = "/root/inspection_binder.pdf"
OUTPUT_PDF = "/root/site_inspection_packet.pdf"
TARGET_STATION = "ST-204"
TARGET_DATES = {"2026-02-14", "2026-03-03"}

reader = PdfReader(INPUT_PDF)
writer = PdfWriter()

carry_forward = False
for page in reader.pages:
    text = page.extract_text() or ""
    explicit_match = (
        f"Station Number: {TARGET_STATION}" in text
        and any(f"Inspection Date: {date}" in text for date in TARGET_DATES)
    )
    continuation_page = "Continuation of previous inspection entry" in text

    if explicit_match:
        writer.add_page(page)
        carry_forward = True
    elif continuation_page and carry_forward:
        writer.add_page(page)
    else:
        carry_forward = False

with open(OUTPUT_PDF, "wb") as f:
    writer.write(f)
PY
