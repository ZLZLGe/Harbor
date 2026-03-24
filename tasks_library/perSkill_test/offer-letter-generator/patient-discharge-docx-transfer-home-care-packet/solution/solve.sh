#!/bin/bash
set -euo pipefail

cat > /tmp/fill_discharge_packet.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3

import json

from docx import Document

TEMPLATE = "/root/discharge_packet_template.docx"
DATA_FILE = "/root/patient_discharge_data.json"
OUTPUT = "/root/discharge_packet_final.docx"


def set_paragraph_text(paragraph, text):
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def replace_scalars(text, scalar_values):
    for key, value in scalar_values.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def apply_remote_followup_condition(text, data):
    start = "{{IF_REMOTE_FOLLOWUP}}"
    end = "{{END_IF_REMOTE_FOLLOWUP}}"
    while start in text and end in text:
        prefix, rest = text.split(start, 1)
        inner, suffix = rest.split(end, 1)
        replacement = inner if data.get("REMOTE_FOLLOWUP_REQUIRED") == "Yes" else ""
        text = prefix + replacement + suffix
    return text


def replace_in_paragraph(paragraph, scalar_values, data):
    original = "".join(run.text for run in paragraph.runs) if paragraph.runs else paragraph.text
    if not original:
        return

    updated = apply_remote_followup_condition(original, data)
    updated = replace_scalars(updated, scalar_values)

    if updated != original:
        set_paragraph_text(paragraph, updated)


def set_cell_text(cell, text):
    if cell.paragraphs:
        set_paragraph_text(cell.paragraphs[0], text)
        for paragraph in cell.paragraphs[1:]:
            set_paragraph_text(paragraph, "")
    else:
        cell.text = text


def populate_table(table, items, fields):
    if len(table.rows) < 2 or not items:
        return

    for column_index, field in enumerate(fields):
        set_cell_text(table.rows[1].cells[column_index], str(items[0][field]))

    for item in items[1:]:
        row = table.add_row()
        for column_index, field in enumerate(fields):
            row.cells[column_index].text = str(item[field])


def expand_dynamic_tables_in_container(container, data):
    for table in container.tables:
        if table.rows:
            header = [cell.text.strip() for cell in table.rows[0].cells]
            if header == ["Medication", "Dose", "Schedule", "Purpose"]:
                populate_table(table, data["MEDICATIONS"], ["NAME", "DOSE", "SCHEDULE", "PURPOSE"])
            elif header == ["Clinic", "Date/Time", "Location", "Notes"]:
                populate_table(table, data["FOLLOW_UP_APPOINTMENTS"], ["CLINIC", "WHEN", "LOCATION", "NOTES"])

        for row in table.rows:
            for cell in row.cells:
                expand_dynamic_tables_in_container(cell, data)


def replace_everywhere_in_container(container, scalar_values, data):
    for paragraph in container.paragraphs:
        replace_in_paragraph(paragraph, scalar_values, data)

    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                replace_everywhere_in_container(cell, scalar_values, data)


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    scalar_values = {key: value for key, value in data.items() if not isinstance(value, list)}
    doc = Document(TEMPLATE)

    expand_dynamic_tables_in_container(doc, data)
    replace_everywhere_in_container(doc, scalar_values, data)

    for section in doc.sections:
        replace_everywhere_in_container(section.header, scalar_values, data)
        replace_everywhere_in_container(section.footer, scalar_values, data)

    doc.save(OUTPUT)
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/fill_discharge_packet.py
