#!/bin/bash
set -euo pipefail

cat > /tmp/fill_festival_run_of_show.py <<'PY'
#!/usr/bin/env python3

import json
import re

from docx import Document

TEMPLATE = "/root/festival_run_of_show_template.docx"
DATA_FILE = "/root/festival_run_of_show_data.json"
OUTPUT = "/root/festival_run_of_show_final.docx"


def replace_in_paragraph(paragraph, data):
    text = paragraph.text
    if not text:
        return

    condition_start = "{{IF_RAIN_PLAN}}"
    condition_end = "{{END_IF_RAIN_PLAN}}"
    if condition_start in text and condition_end in text:
        if data.get("RAIN_PLAN_ENABLED") == "Yes":
            new_text = text.replace(condition_start, "").replace(condition_end, "")
            for key, value in data.items():
                new_text = new_text.replace(f"{{{{{key}}}}}", str(value))
        else:
            new_text = ""
    else:
        pattern = r"\{\{([A-Z0-9_]+)\}\}"
        matches = re.findall(pattern, text)
        if not matches:
            return

        new_text = text
        for key in matches:
            if key in data:
                new_text = new_text.replace(f"{{{{{key}}}}}", str(data[key]))

    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""


def walk_table(table, data):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                replace_in_paragraph(paragraph, data)
            for nested_table in cell.tables:
                walk_table(nested_table, data)


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    doc = Document(TEMPLATE)

    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph, data)

    for table in doc.tables:
        walk_table(table, data)

    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            replace_in_paragraph(paragraph, data)
        for paragraph in section.footer.paragraphs:
            replace_in_paragraph(paragraph, data)

    doc.save(OUTPUT)


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_festival_run_of_show.py
