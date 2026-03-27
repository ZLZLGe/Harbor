import json
import re
from pathlib import Path

from docx import Document

OUTPUT_FILE = "/root/transfer2_merged_offer_letter.docx"
PROFILE = "/root/profile_core.json"
TERMS = "/root/offer_terms.json"


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


def merged_data():
    profile = json.loads(Path(PROFILE).read_text())
    terms = json.loads(Path(TERMS).read_text())
    result = dict(profile)
    result.update(terms)
    return result


def test_output_exists():
    assert Path(OUTPUT_FILE).exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_matches_merged_inputs():
    doc = Document(OUTPUT_FILE)
    text = get_all_text(doc)
    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    assert not leftovers, f"Unreplaced placeholders remain: {leftovers}"

    data = merged_data()
    required_keys = [
        "DATE",
        "CANDIDATE_FULL_NAME",
        "POSITION",
        "DEPARTMENT",
        "BASE_SALARY",
        "SIGNING_BONUS",
        "EQUITY_SHARES",
        "MANAGER_NAME",
        "HR_NAME",
    ]
    for key in required_keys:
        assert str(data[key]) in text

    assert "{{IF_RELOCATION}}" not in text
    assert "{{END_IF_RELOCATION}}" not in text
    if str(data.get("RELOCATION_PACKAGE", "")).lower() == "yes":
        assert str(data["RELOCATION_AMOUNT"]) in text
    else:
        assert str(data.get("RELOCATION_AMOUNT", "")) not in text
