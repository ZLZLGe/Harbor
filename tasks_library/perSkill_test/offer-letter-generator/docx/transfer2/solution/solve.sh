#!/bin/bash
set -euo pipefail

cat > /tmp/fill_docx.py << 'PY'
#!/usr/bin/env python3
import json
import re
from docx import Document

TEMPLATE = "/root/offer_letter_template.docx"
PROFILE = "/root/profile_core.json"
TERMS = "/root/offer_terms.json"
OUTPUT = "/root/transfer2_merged_offer_letter.docx"


def truthy(value):
    return str(value).strip().lower() in {"yes", "true", "1", "y"}


def condition_enabled(key, data):
    candidates = [
        key,
        f"{key}_PACKAGE",
        f"{key}_ENABLED",
    ]
    for candidate in candidates:
        if candidate in data:
            return truthy(data.get(candidate, ""))
    return False


def load_merged_data():
    with open(PROFILE, "r", encoding="utf-8") as f:
        profile = json.load(f)
    with open(TERMS, "r", encoding="utf-8") as f:
        terms = json.load(f)
    merged = dict(profile)
    merged.update(terms)
    return merged


def apply_conditionals(text, data):
    pattern = re.compile(r"\{\{IF_([A-Z0-9_]+)\}\}(.*?)\{\{END_IF_\1\}\}")
    while True:
        match = pattern.search(text)
        if not match:
            break
        key = match.group(1)
        body = match.group(2)
        replacement = body if condition_enabled(key, data) else ""
        text = text[: match.start()] + replacement + text[match.end() :]
    return text


def replace_placeholders(text, data):
    text = apply_conditionals(text, data)

    def repl(match):
        key = match.group(1)
        return str(data[key]) if key in data else match.group(0)

    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, text)


def apply_to_paragraph(paragraph, data):
    old_text = paragraph.text
    new_text = replace_placeholders(old_text, data)
    if new_text == old_text or not paragraph.runs:
        return
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""


def process_table(table, data):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                apply_to_paragraph(paragraph, data)
            for nested in cell.tables:
                process_table(nested, data)


def process_document(doc, data):
    for paragraph in doc.paragraphs:
        apply_to_paragraph(paragraph, data)
    for table in doc.tables:
        process_table(table, data)
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            apply_to_paragraph(paragraph, data)
        for paragraph in section.footer.paragraphs:
            apply_to_paragraph(paragraph, data)


def main():
    data = load_merged_data()
    doc = Document(TEMPLATE)
    process_document(doc, data)
    doc.save(OUTPUT)


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_docx.py
