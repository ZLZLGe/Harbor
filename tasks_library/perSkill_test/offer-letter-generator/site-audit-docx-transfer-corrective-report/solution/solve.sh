#!/bin/bash
set -euo pipefail

cat > /tmp/fill_site_audit_report.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3

import json

from docx import Document

TEMPLATE = "/root/site_audit_report_template.docx"
DATA_FILE = "/root/site_audit_findings.json"
OUTPUT = "/root/site_audit_report_final.docx"


def set_paragraph_text(paragraph, text):
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def replace_scalars(text, values):
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def apply_critical_findings_condition(text, data):
    start = "{{IF_CRITICAL_FINDINGS}}"
    end = "{{END_IF_CRITICAL_FINDINGS}}"
    while start in text and end in text:
        prefix, rest = text.split(start, 1)
        inner, suffix = rest.split(end, 1)
        replacement = inner if data.get("CRITICAL_FINDINGS") == "Yes" else ""
        text = prefix + replacement + suffix
    return text


def replace_in_paragraph(paragraph, scalar_values, data):
    original = "".join(run.text for run in paragraph.runs) if paragraph.runs else paragraph.text
    if not original:
        return

    updated = apply_critical_findings_condition(original, data)
    updated = replace_scalars(updated, scalar_values)

    if updated != original:
        set_paragraph_text(paragraph, updated)


def walk_container(container, scalar_values, data):
    for paragraph in container.paragraphs:
        replace_in_paragraph(paragraph, scalar_values, data)

    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                walk_container(cell, scalar_values, data)


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    scalar_values = {key: value for key, value in data.items() if not isinstance(value, (list, dict))}
    doc = Document(TEMPLATE)

    walk_container(doc, scalar_values, data)

    for section in doc.sections:
        walk_container(section.header, scalar_values, data)
        walk_container(section.footer, scalar_values, data)

    doc.save(OUTPUT)
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/fill_site_audit_report.py
