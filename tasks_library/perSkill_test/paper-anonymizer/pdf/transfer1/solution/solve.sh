#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import os
from pypdf import PdfReader, PdfWriter

pairs = [
    ("paper1.pdf", 0),
    ("paper2.pdf", 0),
    ("paper3.pdf", 0),
]

os.makedirs("/root/output", exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)

writer = PdfWriter()
index_rows = []

for idx, (file_name, page_index) in enumerate(pairs, start=1):
    reader = PdfReader(f"/root/{file_name}")
    writer.add_page(reader.pages[page_index])
    index_rows.append(
        {
            "packet_page": idx,
            "source_file": file_name,
            "source_page": page_index + 1,
        }
    )

with open("/root/output/transfer1_packet.pdf", "wb") as f:
    writer.write(f)

with open("/root/reports/transfer1_packet_index.json", "w", encoding="utf-8") as f:
    json.dump({"pages": index_rows}, f, indent=2)
PY
