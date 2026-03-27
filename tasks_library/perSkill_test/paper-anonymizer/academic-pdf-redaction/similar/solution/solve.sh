#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import os
import fitz

INPUTS = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
OUTPUT_DIR = "/root/redacted/similar"
REPORT_PATH = "/root/reports/similar_redaction_report.json"

PATTERNS = {
    "paper1.pdf": [
        "Yueqian Lin", "Zhengmian Hu", "Qinsi Wang", "Yudong Liu",
        "Hengfan Zhang", "Jayakumar Subramanian", "Nikos Vlassis",
        "Hai Li", "Helen Li", "Yiran Chen", "Duke University", "Adobe",
        "@duke.edu", "@adobe.com", "arXiv:2509.26542",
    ],
    "paper2.pdf": [
        "Jiatong Shi", "Yueqian Lin", "Xinyi Bai", "Keyi Zhang",
        "Yuning Wu", "Yuxun Tang", "Yifeng Yu", "Qin Jin", "Shinji Watanabe",
        "Carnegie Mellon", "Duke Kunshan", "Cornell", "Renmin University",
        "Georgia Tech", "@cmu.edu", "@duke.edu", "@cornell.edu", "@ruc.edu.cn",
        "@gatech.edu", "10.21437/Interspeech.2024-33", "Shengyuan Xu", "Pengcheng Zhu",
    ],
    "paper3.pdf": [
        "Yueqian Lin", "Yuzhe Fu", "Jingyang Zhang", "Yudong Liu", "Jianyi Zhang",
        "Jingwei Sun", "Hai Li", "Yiran Chen", "Duke University", "yl768@duke.edu",
        "Equal contribution", "ICML Workshop on Machine Learning for Audio",
    ],
}


def first_references_page(doc: fitz.Document):
    for i, page in enumerate(doc):
        if "references" in page.get_text().lower():
            return i
    return None


os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)
rows = []

for filename in INPUTS:
    inp = os.path.join("/root", filename)
    out = os.path.join(OUTPUT_DIR, filename)
    doc = fitz.open(inp)
    original_text_len = sum(len(p.get_text()) for p in doc)
    ref_page = first_references_page(doc)
    hits = 0

    for page_index, page in enumerate(doc):
        if ref_page is not None and page_index >= ref_page:
            continue
        for pattern in PATTERNS[filename]:
            rects = page.search_for(pattern)
            hits += len(rects)
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(out)
    doc.close()

    out_doc = fitz.open(out)
    redacted_text_len = sum(len(p.get_text()) for p in out_doc)
    out_doc.close()

    ratio = 0.0 if original_text_len == 0 else redacted_text_len / original_text_len
    rows.append({
        "file": filename,
        "redaction_hits": hits,
        "retained_ratio": round(ratio, 4),
    })

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)
PY
