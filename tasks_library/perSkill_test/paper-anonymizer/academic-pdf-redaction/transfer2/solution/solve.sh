#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import os
import fitz

FILES = ["paper2.pdf", "paper3.pdf"]
OUT_DIR = "/root/redacted/transfer2"
REPORT = "/root/reports/transfer2_quality.md"

PATTERNS = {
    "paper2.pdf": [
        "Jiatong Shi", "Yueqian Lin", "Xinyi Bai", "Keyi Zhang", "Qin Jin",
        "Carnegie Mellon", "Duke Kunshan", "Cornell", "Renmin University", "Georgia Tech",
        "@cmu.edu", "@duke.edu", "@cornell.edu", "10.21437/Interspeech.2024-33",
    ],
    "paper3.pdf": [
        "Yueqian Lin", "Yuzhe Fu", "Jingyang Zhang", "Yudong Liu", "Jianyi Zhang", "Jingwei Sun",
        "Duke University", "yl768@duke.edu", "Equal contribution", "ICML Workshop on Machine Learning for Audio",
    ],
}


def first_references_page(doc: fitz.Document):
    for i, page in enumerate(doc):
        if "references" in page.get_text().lower():
            return i
    return None


os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)
rows = []

for filename in FILES:
    in_path = os.path.join("/root", filename)
    out_path = os.path.join(OUT_DIR, filename)

    doc = fitz.open(in_path)
    original_len = sum(len(p.get_text()) for p in doc)
    ref_page = first_references_page(doc)

    for i, page in enumerate(doc):
        if ref_page is not None and i >= ref_page:
            continue
        for term in PATTERNS[filename]:
            for rect in page.search_for(term):
                page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(out_path)
    doc.close()

    out_doc = fitz.open(out_path)
    redacted_len = sum(len(p.get_text()) for p in out_doc)
    out_doc.close()

    ratio = 0.0 if original_len == 0 else redacted_len / original_len
    status = "PASS" if ratio >= 0.75 else "FAIL"
    rows.append((filename, original_len, redacted_len, ratio, status))

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# Transfer2 Redaction Quality\n\n")
    f.write("| file | original_chars | redacted_chars | retained_ratio | status |\n")
    f.write("|---|---:|---:|---:|---|\n")
    for filename, original_len, redacted_len, ratio, status in rows:
        f.write(f"| {filename} | {original_len} | {redacted_len} | {ratio:.4f} | {status} |\n")
PY
