#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import os
import re
from pypdf import PdfReader

keywords = ["voice", "data", "pruning"]
files = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

texts = {}
for fname in files:
    reader = PdfReader(f"/root/{fname}")
    content = "\n".join((p.extract_text() or "") for p in reader.pages).lower()
    texts[fname] = content

os.makedirs("/root/reports", exist_ok=True)
with open("/root/reports/transfer3_keyword_inventory.md", "w", encoding="utf-8") as f:
    f.write("# Transfer3 Keyword Inventory\n\n")
    f.write("| keyword | paper1 | paper2 | paper3 | total |\n")
    f.write("|---|---:|---:|---:|---:|\n")
    for kw in keywords:
        counts = []
        for fname in files:
            count = len(re.findall(rf"\\b{re.escape(kw)}\\b", texts[fname]))
            counts.append(count)
        total = sum(counts)
        f.write(f"| {kw} | {counts[0]} | {counts[1]} | {counts[2]} | {total} |\n")
PY
