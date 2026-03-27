#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import os
import fitz

FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
OUT_DIR = "/root/redacted/transfer3"
MANIFEST_PATH = "/root/reports/transfer3_manifest.json"

TOKENS = {
    "paper1.pdf": {
        "author": ["Yueqian Lin", "Zhengmian Hu", "Qinsi Wang", "Yudong Liu", "Hengfan Zhang", "Hai Li"],
        "identifier": ["@duke.edu", "@adobe.com", "arXiv:2509.26542", "Duke University", "Adobe"],
    },
    "paper2.pdf": {
        "author": ["Jiatong Shi", "Yueqian Lin", "Xinyi Bai", "Keyi Zhang", "Qin Jin"],
        "identifier": ["@cmu.edu", "@duke.edu", "@cornell.edu", "10.21437/Interspeech.2024-33", "Carnegie Mellon"],
    },
    "paper3.pdf": {
        "author": ["Yueqian Lin", "Yuzhe Fu", "Jingyang Zhang", "Yudong Liu", "Jianyi Zhang"],
        "identifier": ["yl768@duke.edu", "Equal contribution", "ICML Workshop on Machine Learning for Audio", "Duke University"],
    },
}


def first_references_page(doc: fitz.Document):
    for i, page in enumerate(doc):
        if "references" in page.get_text().lower():
            return i
    return None


os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("/root/reports", exist_ok=True)
manifest = {"documents": []}

for filename in FILES:
    in_path = os.path.join("/root", filename)
    out_path = os.path.join(OUT_DIR, filename)

    in_doc = fitz.open(in_path)
    in_pages = len(in_doc)
    original_len = sum(len(p.get_text()) for p in in_doc)
    ref_page = first_references_page(in_doc)

    author_hits = 0
    identifier_hits = 0

    for i, page in enumerate(in_doc):
        if ref_page is not None and i >= ref_page:
            continue
        for token in TOKENS[filename]["author"]:
            rects = page.search_for(token)
            author_hits += len(rects)
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))
        for token in TOKENS[filename]["identifier"]:
            rects = page.search_for(token)
            identifier_hits += len(rects)
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    in_doc.save(out_path)
    in_doc.close()

    out_doc = fitz.open(out_path)
    out_pages = len(out_doc)
    redacted_len = sum(len(p.get_text()) for p in out_doc)
    out_doc.close()

    ratio = 0.0 if original_len == 0 else redacted_len / original_len
    manifest["documents"].append(
        {
            "file": filename,
            "author_tokens_removed": author_hits,
            "identifier_tokens_removed": identifier_hits,
            "retained_ratio": round(ratio, 4),
            "page_count_unchanged": in_pages == out_pages,
        }
    )

with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
PY
