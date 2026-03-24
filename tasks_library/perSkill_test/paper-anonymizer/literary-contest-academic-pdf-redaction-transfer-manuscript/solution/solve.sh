#!/bin/bash
set -euo pipefail

python3 <<'PY'
import os
import tempfile

import fitz
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject

INPUT_PATH = "/root/submission/manuscript_packet.pdf"
OUTPUT_PATH = "/root/jury_ready/manuscript_blinded.pdf"

TEXT_PATTERNS = [
    "Author: Mara Ellison",
    "Represented by Northbank Literary Agency",
    "Website: www.maraellisonwrites.com",
    "Contact: mara@northbanklit.com | +1 212-555-0199",
    "Awards: Winner of the 2023 Halcyon Prize; shortlisted for the Aurora Quill Award",
    "Mara Ellison | Glass Harbor",
]


def strip_links_and_metadata(input_path: str, output_path: str) -> None:
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        if "/Annots" in page:
            page[NameObject("/Annots")] = ArrayObject()
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": "Glass Harbor Manuscript",
            "/Author": "",
            "/Subject": "",
            "/Keywords": "",
            "/Creator": "",
            "/Producer": "",
        }
    )

    with open(output_path, "wb") as handle:
        writer.write(handle)


def verify_output(input_path: str, output_path: str) -> None:
    original = fitz.open(input_path)
    blinded = fitz.open(output_path)

    original_text = sum(len(page.get_text()) for page in original)
    blinded_text = sum(len(page.get_text()) for page in blinded)

    if len(original) != len(blinded):
        raise ValueError(f"page count changed: {len(original)} -> {len(blinded)}")
    if blinded_text < original_text * 0.7:
        raise ValueError(f"too much text removed: retained {blinded_text / original_text:.1%}")

    original.close()
    blinded.close()


doc = fitz.open(INPUT_PATH)

for page in doc:
    for pattern in TEXT_PATTERNS:
        for rect in page.search_for(pattern):
            page.add_redact_annot(rect, fill=(0, 0, 0))
    page.apply_redactions()

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
    temp_path = handle.name

doc.set_metadata({})
doc.save(temp_path)
doc.close()

strip_links_and_metadata(temp_path, OUTPUT_PATH)
os.remove(temp_path)

verify_output(INPUT_PATH, OUTPUT_PATH)
PY
