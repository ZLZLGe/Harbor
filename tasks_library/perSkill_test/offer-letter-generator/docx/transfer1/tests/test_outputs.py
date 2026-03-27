import json
import re
from pathlib import Path

from docx import Document

OUTPUT_FILE = "/root/transfer1_selected_offer_letter.docx"
POOL_FILE = "/root/candidate_pool.json"


def get_all_text(doc):
    parts = []
    for para in doc.paragraphs:
        parts.append(para.text)

    def extract_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    parts.append(para.text)
                for nested in cell.tables:
                    extract_table(nested)

    for table in doc.tables:
        extract_table(table)

    for section in doc.sections:
        for para in section.header.paragraphs:
            parts.append(para.text)
        for para in section.footer.paragraphs:
            parts.append(para.text)

    return "\n".join(parts)


def load_selected_candidate():
    payload = json.loads(Path(POOL_FILE).read_text())
    selected_id = payload["selected_candidate_id"]
    for candidate in payload["candidates"]:
        if candidate.get("candidate_id") == selected_id:
            return candidate
    raise AssertionError("selected candidate not found")


def test_output_exists():
    assert Path(OUTPUT_FILE).exists(), f"Missing output file: {OUTPUT_FILE}"


def test_content_matches_selected_candidate_and_tokens_removed():
    doc = Document(OUTPUT_FILE)
    text = get_all_text(doc)
    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    assert not leftovers, f"Unreplaced placeholders remain: {leftovers}"

    selected = load_selected_candidate()
    required_keys = [
        "CANDIDATE_FULL_NAME",
        "POSITION",
        "DEPARTMENT",
        "BASE_SALARY",
        "SIGNING_BONUS",
        "EQUITY_SHARES",
        "MANAGER_NAME",
        "HR_NAME",
        "PTO_DAYS",
    ]
    for key in required_keys:
        assert str(selected[key]) in text

    assert "{{IF_RELOCATION}}" not in text
    assert "{{END_IF_RELOCATION}}" not in text
    if str(selected.get("RELOCATION_PACKAGE", "")).lower() == "yes":
        assert str(selected["RELOCATION_AMOUNT"]) in text
        assert str(selected["RELOCATION_DAYS"]) in text
    else:
        assert str(selected.get("RELOCATION_AMOUNT", "")) not in text
