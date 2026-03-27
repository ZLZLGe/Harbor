#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import os
import re
from pypdf import PdfReader

FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
OUT_PATH = "/root/reports/similar_document_profile.json"

os.makedirs("/root/reports", exist_ok=True)
documents = []

for fname in FILES:
    reader = PdfReader(f"/root/{fname}")
    page_texts = []
    for page in reader.pages:
        page_texts.append(page.extract_text() or "")

    full_text = "\n".join(page_texts)
    normalized = re.sub(r"\s+", " ", full_text).strip()

    documents.append(
        {
            "file": fname,
            "page_count": len(reader.pages),
            "text_chars": len(full_text),
            "non_empty_pages": sum(1 for t in page_texts if t.strip()),
            "sample_excerpt": normalized[:120],
        }
    )

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"documents": documents}, f, indent=2)
PY
