#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import csv
import os
import fitz

INPUTS = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
OUT_DIR = "/root/redacted/transfer1"
CSV_PATH = "/root/reports/transfer1_matrix.csv"

PATTERNS = {
    "paper1.pdf": {
        "author": ["Yueqian Lin", "Zhengmian Hu", "Qinsi Wang", "Yudong Liu", "Hengfan Zhang"],
        "affiliation": ["Duke University", "Adobe"],
        "identifier": ["@duke.edu", "@adobe.com", "arXiv:2509.26542"],
    },
    "paper2.pdf": {
        "author": ["Jiatong Shi", "Yueqian Lin", "Xinyi Bai", "Keyi Zhang", "Qin Jin"],
        "affiliation": ["Carnegie Mellon", "Duke Kunshan", "Cornell", "Renmin University", "Georgia Tech"],
        "identifier": ["@cmu.edu", "@duke.edu", "@cornell.edu", "10.21437/Interspeech.2024-33"],
    },
    "paper3.pdf": {
        "author": ["Yueqian Lin", "Yuzhe Fu", "Jingyang Zhang", "Yudong Liu", "Jianyi Zhang"],
        "affiliation": ["Duke University"],
        "identifier": ["yl768@duke.edu", "Equal contribution", "ICML Workshop on Machine Learning for Audio"],
    },
}


def first_references_page(doc: fitz.Document):
    for i, page in enumerate(doc):
        if "references" in page.get_text().lower():
            return i
    return None


os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)
rows = []

for filename in INPUTS:
    in_path = os.path.join("/root", filename)
    out_path = os.path.join(OUT_DIR, filename)

    doc = fitz.open(in_path)
    original_len = sum(len(p.get_text()) for p in doc)
    ref_page = first_references_page(doc)

    counts = {"author": 0, "affiliation": 0, "identifier": 0}
    for i, page in enumerate(doc):
        if ref_page is not None and i >= ref_page:
            continue
        for kind, terms in PATTERNS[filename].items():
            for term in terms:
                rects = page.search_for(term)
                counts[kind] += len(rects)
                for rect in rects:
                    page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(out_path)
    doc.close()

    out_doc = fitz.open(out_path)
    redacted_len = sum(len(p.get_text()) for p in out_doc)
    out_doc.close()

    ratio = 0.0 if original_len == 0 else redacted_len / original_len
    total_hits = counts["author"] + counts["affiliation"] + counts["identifier"]
    rows.append([
        filename,
        counts["author"],
        counts["affiliation"],
        counts["identifier"],
        total_hits,
        f"{ratio:.4f}",
    ])

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["file", "author_hits", "affiliation_hits", "identifier_hits", "total_hits", "retained_ratio"])
    writer.writerows(rows)
PY
