from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


OUTPUT_FILE = Path("/app/output/vendor_addendum_final.docx")
INPUT_FILE = Path("/app/vendor_addendum_redline.docx")
DECISIONS_FILE = Path("/app/review_decisions.json")
PROTECTED_HASHES = Path("/opt/documents-task/protected_hashes.json")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REVIEW_NS = "urn:northharbor:review-manifest"
NS = {"w": W_NS, "rv": REVIEW_NS}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protected() -> dict:
    return json.loads(PROTECTED_HASHES.read_text(encoding="utf-8"))


def table_count(docx_path: Path) -> int:
    with ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return len(root.findall(".//w:tbl", NS))


def paragraph_count(docx_path: Path, members: list[str]) -> int:
    total = 0
    with ZipFile(docx_path) as archive:
        for member in members:
            root = ET.fromstring(archive.read(member))
            total += len(root.findall(".//w:p", NS))
    return total


def manifest_item_count(docx_path: Path) -> int:
    with ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("customXml/item1.xml"))
    return len(root.findall(".//rv:item", NS))


def test_input_files_unchanged() -> None:
    protected = load_protected()["input_files"]
    assert sha256_file(INPUT_FILE) == protected["vendor_addendum_redline.docx"], "Input redline DOCX was modified"
    assert sha256_file(DECISIONS_FILE) == protected["review_decisions.json"], "Input decisions JSON was modified"


def test_skill_files_unchanged_when_present() -> None:
    protected = load_protected()["skill_files"]
    skill_root = Path("/home/appuser/.codex/skills")
    if not protected:
        return

    for rel_path, expected_hash in protected.items():
        current_path = skill_root / rel_path
        assert current_path.exists(), f"Expected skill file missing: {current_path}"
        assert sha256_file(current_path) == expected_hash, f"Skill file was modified: {current_path}"


def test_output_preserves_core_document_structure() -> None:
    assert OUTPUT_FILE.exists(), "Output file missing"

    with ZipFile(OUTPUT_FILE) as archive:
        names = set(archive.namelist())
        assert "word/header1.xml" in names, "Header part missing from final DOCX"
        assert "word/footer1.xml" in names, "Footer part missing from final DOCX"
        assert "word/footnotes.xml" in names, "Footnotes part missing from final DOCX"
        assert "customXml/item1.xml" in names, "Structured review manifest missing from final DOCX"
        assert "word/comments.xml" not in names, "Comments part should not remain in clean final DOCX"

    assert table_count(OUTPUT_FILE) == table_count(INPUT_FILE), "Table structure changed unexpectedly"
    assert paragraph_count(OUTPUT_FILE, ["word/document.xml", "word/header1.xml", "word/footer1.xml"]) >= paragraph_count(
        INPUT_FILE,
        ["word/document.xml", "word/header1.xml", "word/footer1.xml"],
    ) - 8, "Too many document/header/footer paragraphs were removed"
    assert paragraph_count(OUTPUT_FILE, ["word/footnotes.xml"]) == paragraph_count(
        INPUT_FILE,
        ["word/footnotes.xml"],
    ), "Footnote structure changed unexpectedly"
    assert manifest_item_count(OUTPUT_FILE) == manifest_item_count(INPUT_FILE), "Review-manifest item count changed unexpectedly"


def test_output_is_not_stubbed_or_flattened() -> None:
    assert OUTPUT_FILE.stat().st_size > INPUT_FILE.stat().st_size * 0.60, "Output DOCX looks too small to be a real reconciled document"
