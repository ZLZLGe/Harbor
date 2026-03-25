#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import re

from pypdf import PdfReader, PdfWriter

SOURCE_PATH = "/root/hearing_materials_mixed_source"
MANIFEST_PATH = "/root/bundle_manifest.json"
OUTPUT_PATH = "/root/hearing_exhibit_bundle.pdf"

HEADER_RE = re.compile(
    r"Case:\s*(?P<case_id>HB-\d{2}-\d{3})\s+"
    r"Exhibit:\s*(?P<exhibit_id>EX-\d{2})\s+"
    r"Exhibit Page:\s*(?P<page>\d+)\s+of\s+\d+"
)


def normalize(text: str) -> str:
    return " ".join(text.split())


reader = PdfReader(SOURCE_PATH)
page_lookup = {}

for index, page in enumerate(reader.pages):
    text = normalize(page.extract_text() or "")
    match = HEADER_RE.search(text)
    if match is None:
        raise RuntimeError(f"Unable to parse source page {index + 1}")

    key = (
        match.group("case_id"),
        match.group("exhibit_id"),
        int(match.group("page")),
    )
    page_lookup[key] = index

with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
    manifest = json.load(handle)

writer = PdfWriter()

for request in manifest["requests"]:
    case_id = request["case_id"]
    exhibit_id = request["exhibit_id"]
    for exhibit_page in range(request["start_page"], request["end_page"] + 1):
        key = (case_id, exhibit_id, exhibit_page)
        if key not in page_lookup:
            raise KeyError(f"Missing page for {key}")
        writer.add_page(reader.pages[page_lookup[key]])

with open(OUTPUT_PATH, "wb") as handle:
    writer.write(handle)
PY
