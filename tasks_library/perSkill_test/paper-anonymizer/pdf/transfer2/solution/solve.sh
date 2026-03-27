#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import csv
import os
from pypdf import PdfReader, PdfWriter

reader = PdfReader("/root/paper1.pdf")
os.makedirs("/root/output/transfer2_pages", exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)

rows = []
for i in range(4):
    writer = PdfWriter()
    writer.add_page(reader.pages[i])

    out_name = f"page_{i + 1:03d}.pdf"
    out_path = f"/root/output/transfer2_pages/{out_name}"
    with open(out_path, "wb") as f:
        writer.write(f)

    text = reader.pages[i].extract_text() or ""
    rows.append([i + 1, out_name, len(text)])

with open("/root/reports/transfer2_split_manifest.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["page_index", "output_file", "char_count"])
    writer.writerows(rows)
PY
