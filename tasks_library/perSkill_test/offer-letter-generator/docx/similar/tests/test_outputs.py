import json
import re
from pathlib import Path

from docx import Document

OUTPUT_FILE = "/root/similar_offer_letter_filled.docx"
DATA_FILE = "/root/employee_data.json"


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
        for table in section.header.tables:
            extract_table(table)
        for para in section.footer.paragraphs:
            parts.append(para.text)
        for table in section.footer.tables:
            extract_table(table)

    return "\n".join(parts)


def test_output_exists_and_is_valid_docx():
    assert Path(OUTPUT_FILE).exists(), f"Output file not found: {OUTPUT_FILE}"
    Document(OUTPUT_FILE)


def test_placeholders_removed_and_core_values_present():
    doc = Document(OUTPUT_FILE)
    text = get_all_text(doc)

    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    assert not leftovers, f"Unreplaced placeholders remain: {leftovers}"

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_fields = [
        "DATE",
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

    for key in required_fields:
        assert str(data[key]) in text, f"Expected value for {key} not found"


def test_relocation_conditional_processed():
    doc = Document(OUTPUT_FILE)
    text = get_all_text(doc)

    assert "{{IF_RELOCATION}}" not in text
    assert "{{END_IF_RELOCATION}}" not in text

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if str(data.get("RELOCATION_PACKAGE", "")).lower() == "yes":
        assert str(data["RELOCATION_AMOUNT"]) in text
        assert str(data["RELOCATION_DAYS"]) in text
