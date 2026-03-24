import json
from pathlib import Path

from pypdf import PdfReader


ARTIFACT_PATH = Path("/app/artifacts/regulatory_submission_packet.pdf")
MANIFEST_PATH = Path("/app/workspace/input/submission_manifest.json")


def normalize(text):
    return " ".join((text or "").split())


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_output():
    assert ARTIFACT_PATH.is_file(), f"Missing output PDF: {ARTIFACT_PATH}"
    return PdfReader(str(ARTIFACT_PATH))


def page_text(reader, page_number):
    return normalize(reader.pages[page_number - 1].extract_text())


def test_output_exists_and_page_count():
    manifest = load_manifest()
    reader = load_output()
    assert len(reader.pages) == 1 + len(manifest["assembly_order"])


def test_cover_page_contains_required_fields_and_exhibits():
    manifest = load_manifest()
    reader = load_output()
    cover_text = page_text(reader, 1)

    assert manifest["packet_title"] in cover_text
    assert f"Packet title: {manifest['packet_title']}" in cover_text
    assert f"Packet ID: {manifest['packet_id']}" in cover_text
    assert f"Applicant: {manifest['applicant']}" in cover_text
    assert f"Facility: {manifest['facility']}" in cover_text
    assert f"Permit number: {manifest['permit_number']}" in cover_text
    assert f"Submission deadline: {manifest['submission_deadline']}" in cover_text
    assert f"Prepared by: {manifest['prepared_by']}" in cover_text
    assert "Included exhibits" in cover_text

    for item in manifest["assembly_order"]:
        assert f"{item['section_code']}. {item['section_title']}" in cover_text


def test_metadata_title_matches_manifest():
    manifest = load_manifest()
    reader = load_output()
    assert reader.metadata.title == manifest["output_title"]


def test_pages_follow_manifest_order_and_are_upright():
    manifest = load_manifest()
    reader = load_output()

    for index, item in enumerate(manifest["assembly_order"], start=2):
        text = page_text(reader, index)
        assert item["page_marker"] in text, f"Expected marker {item['page_marker']} on output page {index}"
        page = reader.pages[index - 1]
        assert int(page.get("/Rotate", 0)) % 360 == 0, f"Output page {index} is still rotated"


def test_excluded_pages_are_not_present():
    manifest = load_manifest()
    reader = load_output()
    all_text = " ".join(page_text(reader, index + 1) for index in range(len(reader.pages)))

    for marker in manifest["excluded_page_markers"]:
        assert marker not in all_text, f"Excluded marker leaked into output: {marker}"
