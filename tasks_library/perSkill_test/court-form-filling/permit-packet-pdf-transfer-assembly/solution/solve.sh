#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pypdf import PdfReader, PdfWriter

OUTPUT_PATH = "/root/permit-submission-packet.pdf"
PAGE_PLAN = [
    ("/root/permit-application.pdf", 1),
    ("/root/permit-application.pdf", 0),
    ("/root/site-inspection.pdf", 2),
    ("/root/site-inspection.pdf", 0),
    ("/root/structural-attachments.pdf", 1),
]

readers = {}
writer = PdfWriter()

for pdf_path, zero_based_page_index in PAGE_PLAN:
    if pdf_path not in readers:
        readers[pdf_path] = PdfReader(pdf_path)
    writer.add_page(readers[pdf_path].pages[zero_based_page_index])

with open(OUTPUT_PATH, "wb") as output_file:
    writer.write(output_file)
PY

echo "Wrote /root/permit-submission-packet.pdf"
