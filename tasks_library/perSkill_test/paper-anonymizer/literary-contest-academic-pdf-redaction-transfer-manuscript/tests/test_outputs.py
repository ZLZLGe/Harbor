"""Tests for the literary contest manuscript anonymization task."""

from pathlib import Path

import fitz
from pypdf import PdfReader

INPUT_PATH = Path("/root/submission/manuscript_packet.pdf")
OUTPUT_PATH = Path("/root/jury_ready/manuscript_blinded.pdf")

IDENTIFYING_TEXT = [
    "Mara Ellison",
    "Northbank Literary Agency",
    "www.maraellisonwrites.com",
    "mara@northbanklit.com",
    "+1 212-555-0199",
    "Halcyon Prize",
    "Aurora Quill Award",
    "Mara Ellison | Glass Harbor",
]

PRESERVED_TEXT = [
    "GLASS HARBOR",
    "Lantern Prize novella submission",
    "Chapter I",
    "Chapter II",
    "Chapter III",
    "The harbor bells started before dawn",
    "Footnote 1. Tide book is the dockside ledger used by ferry clerks",
    "Footnote 2. The singers are volunteer mourners",
    "Footnote 3. Beacon houses once stored emergency charts",
    "choosing noise over silence and testimony over ceremony",
]


def read_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_metadata(path: Path) -> dict[str, str]:
    reader = PdfReader(str(path))
    raw = reader.metadata or {}
    return {str(key): str(value or "") for key, value in raw.items()}


def read_uri_links(path: Path) -> list[str]:
    doc = fitz.open(path)
    uris: list[str] = []
    for page in doc:
        for link in page.get_links():
            if link.get("uri"):
                uris.append(link["uri"])
    doc.close()
    return uris


def test_output_exists_and_page_count_is_preserved():
    assert OUTPUT_PATH.exists(), "missing output PDF"

    input_reader = PdfReader(str(INPUT_PATH))
    output_reader = PdfReader(str(OUTPUT_PATH))

    assert len(output_reader.pages) == len(input_reader.pages) == 4


def test_identifying_text_is_removed():
    output_text = read_text(OUTPUT_PATH)
    leaked = [item for item in IDENTIFYING_TEXT if item in output_text]
    assert not leaked, f"identifying text still present: {leaked}"


def test_literary_content_and_structure_are_preserved():
    input_text = read_text(INPUT_PATH)
    output_text = read_text(OUTPUT_PATH)

    for marker in PRESERVED_TEXT:
        assert marker in output_text, f"missing preserved text: {marker}"

    assert len(output_text) >= len(input_text) * 0.72


def test_metadata_is_sanitized():
    metadata = read_metadata(OUTPUT_PATH)

    assert metadata.get("/Author", "") == ""
    assert metadata.get("/Creator", "") == ""

    all_values = " ".join(metadata.values())
    assert "Mara Ellison" not in all_values
    assert "Northbank" not in all_values


def test_external_links_are_removed():
    assert read_uri_links(OUTPUT_PATH) == []
