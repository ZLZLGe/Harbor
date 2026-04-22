from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from docx import Document


OUTPUT_FILE = Path("/app/output/vendor_addendum_final.docx")
INPUT_FILE = Path("/app/vendor_addendum_redline.docx")
DECISIONS_FILE = Path("/app/review_decisions.json")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REVIEW_NS = "urn:northharbor:review-manifest"
NS = {"w": W_NS, "rv": REVIEW_NS}


def load_xml(docx_path: Path, member: str) -> ET.Element:
    with ZipFile(docx_path) as archive:
        return ET.fromstring(archive.read(member))


def paragraph_texts(docx_path: Path, member: str) -> list[str]:
    root = load_xml(docx_path, member)
    texts: list[str] = []
    for para in root.findall(".//w:p", NS):
        text = "".join(node.text or "" for node in para.iter(f"{{{W_NS}}}t"))
        if text.strip():
            texts.append(text)
    return texts


def all_visible_text(docx_path: Path) -> str:
    members = ["word/document.xml", "word/header1.xml", "word/footer1.xml"]
    return "\n".join(text for member in members for text in paragraph_texts(docx_path, member))


def footnote_text(docx_path: Path) -> str:
    root = load_xml(docx_path, "word/footnotes.xml")
    chunks: list[str] = []
    for footnote in root.findall(".//w:footnote", NS):
        note_id = footnote.get(f"{{{W_NS}}}id", "")
        if note_id in {"-1", "0"}:
            continue
        text = "".join(node.text or "" for node in footnote.iter(f"{{{W_NS}}}t"))
        if text.strip():
            chunks.append(text)
    return "\n".join(chunks)


def table_text(docx_path: Path) -> str:
    root = load_xml(docx_path, "word/document.xml")
    chunks: list[str] = []
    for table in root.findall(".//w:tbl", NS):
        for para in table.findall(".//w:p", NS):
            text = "".join(node.text or "" for node in para.iter(f"{{{W_NS}}}t"))
            if text.strip():
                chunks.append(text)
    return "\n".join(chunks)


def review_manifest(docx_path: Path) -> ET.Element:
    return load_xml(docx_path, "customXml/item1.xml")


def test_output_exists_and_is_valid_docx() -> None:
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    assert OUTPUT_FILE.stat().st_size > 0, "Output DOCX is empty"

    with ZipFile(OUTPUT_FILE) as archive:
        names = set(archive.namelist())
        assert "word/document.xml" in names
        assert "word/header1.xml" in names
        assert "word/footer1.xml" in names
        assert "word/footnotes.xml" in names
        assert "customXml/item1.xml" in names
        assert "word/comments.xml" not in names, "Final DOCX should not keep comments.xml"

    Document(str(OUTPUT_FILE))


def test_review_artifacts_are_fully_removed() -> None:
    with ZipFile(OUTPUT_FILE) as archive:
        for member in ["word/document.xml", "word/header1.xml", "word/footer1.xml", "word/footnotes.xml"]:
            data = archive.read(member).decode("utf-8")
            assert "<w:ins" not in data, f"Tracked insertion still present in {member}"
            assert "<w:del" not in data, f"Tracked deletion still present in {member}"
            assert "commentRangeStart" not in data, f"Comment marker still present in {member}"
            assert "commentRangeEnd" not in data, f"Comment marker still present in {member}"
            assert "commentReference" not in data, f"Comment marker still present in {member}"

        settings = archive.read("word/settings.xml").decode("utf-8")
        assert "trackRevisions" not in settings, "Track revisions flag still present in settings.xml"

        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
        assert "relationships/comments" not in rels, "Comments relationship still present in final package"
        assert "relationships/footnotes" in rels, "Footnotes relationship should remain in final package"

        content_types = archive.read("[Content_Types].xml").decode("utf-8")
        assert "wordprocessingml.comments+xml" not in content_types, "Comments content type still present in final package"
        assert "wordprocessingml.footnotes+xml" in content_types, "Footnotes content type should remain in final package"


def test_final_visible_text_matches_decisions() -> None:
    decisions = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
    assert decisions == {
        "TERM_EXTENSION": "accept",
        "NOTICE_PERIOD": "accept",
        "SECURITY_REVIEW": "accept",
        "USAGE_LOG_RETENTION": "accept",
        "AUDIT_REPORT_WINDOW": "reject",
        "PRICING_HOLD": "reject",
        "LICENSE_COUNT": "accept",
        "SERVICE_CREDIT_CAP": "reject",
    }

    text = all_visible_text(OUTPUT_FILE)

    required_lines = [
        "Vendor Services Addendum - Legal Redline",
        "Confidential - North Harbor Procurement Group",
        "The renewed service term will continue through April 30, 2027.",
        "Either party may elect not to renew by giving 45 days' written notice before the end of the term.",
        "A current security review packet must be returned before the renewal takes effect.",
        "System usage logs must be retained for 180 days following each monthly service period.",
        "Security reporting timing is described in the attached audit note.",
        "Please return a fully signed addendum no later than April 25, 2026.",
        "North Harbor Procurement Group Procurement Operations",
    ]
    for line in required_lines:
        assert line in text, f"Missing expected final text: {line}"

    forbidden_lines = [
        "255,000 per year",
        "18,000 per year",
        "90 days following each monthly service period.",
    ]
    for line in forbidden_lines:
        assert line not in text, f"Rejected or superseded redline still visible: {line}"


def test_footnote_and_table_values_reflect_resolved_redlines() -> None:
    assert (
        "Audit reports must be delivered within 5 business days of written request." in footnote_text(OUTPUT_FILE)
    ), "Resolved footnote text does not reflect the rejected audit-window change"

    text = table_text(OUTPUT_FILE)
    expected_values = [
        "Annual Fee",
        "$248,500 per year",
        "Licensed Users",
        "200 seats",
        "Service Credit Cap",
        "$12,000 per year",
    ]
    for value in expected_values:
        assert value in text, f"Expected table value missing: {value}"


def test_structured_review_manifest_is_resolved() -> None:
    root = review_manifest(OUTPUT_FILE)
    items = root.findall(".//rv:item", NS)
    assert len(items) == 8, "Unexpected review-manifest item count"

    expected = {
        "TERM_EXTENSION": "accept",
        "NOTICE_PERIOD": "accept",
        "SECURITY_REVIEW": "accept",
        "USAGE_LOG_RETENTION": "accept",
        "AUDIT_REPORT_WINDOW": "reject",
        "PRICING_HOLD": "reject",
        "LICENSE_COUNT": "accept",
        "SERVICE_CREDIT_CAP": "reject",
    }
    for item in items:
        decision_key = item.get("decisionKey", "")
        assert item.get("status") == "resolved", f"Review-manifest item is not resolved: {decision_key}"
        assert item.get("resolution") == expected[decision_key], f"Wrong resolution in review manifest: {decision_key}"


def test_clean_output_no_pending_review_metadata_remains() -> None:
    with ZipFile(OUTPUT_FILE) as archive:
        for member in archive.namelist():
            if not member.endswith(".xml"):
                continue
            data = archive.read(member).decode("utf-8", errors="ignore")
            assert "Review Ref:" not in data, f"Review comment text leaked into final output: {member}"
            assert "status=\"pending\"" not in data, f"Pending review metadata leaked into final output: {member}"
