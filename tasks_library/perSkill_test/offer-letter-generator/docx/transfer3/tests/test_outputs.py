import json
import re
from pathlib import Path

from docx import Document

OUTPUT_FILE = "/root/transfer3_overridden_offer_letter.docx"
BASE_FILE = "/root/base_data.json"
OVERRIDES_FILE = "/root/overrides.json"


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


def final_data():
    base = json.loads(Path(BASE_FILE).read_text())
    overrides = json.loads(Path(OVERRIDES_FILE).read_text())
    merged = dict(base)
    merged.update(overrides)
    return merged


def test_output_exists():
    assert Path(OUTPUT_FILE).exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_matches_final_layered_data():
    doc = Document(OUTPUT_FILE)
    text = get_all_text(doc)

    leftovers = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    assert not leftovers, f"Unreplaced placeholders remain: {leftovers}"

    data = final_data()
    required_keys = [
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
        assert str(data["RELOCATION_DAYS"]) in text
    else:
        assert str(data.get("RELOCATION_AMOUNT", "")) not in text
