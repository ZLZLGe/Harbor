#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

REQUEST_PATH = "/root/equipment_request_packet.pdf"
FORM_PATH = "/root/equipment_checkout_form.pdf"
OUTPUT_PATH = "/root/workspace/equipment_checkout_filled.pdf"
WORKDIR = Path("/root/workspace")
FIELD_INFO_PATH = WORKDIR / "field_info.json"
FIELD_VALUES_PATH = WORKDIR / "field_values.json"

EXTRACT_SCRIPT = "/root/.codex/skills/pdf/scripts/extract_form_field_info.py"
FILL_SCRIPT = "/root/.codex/skills/pdf/scripts/fill_fillable_fields.py"

TEXT_PATTERNS = {
    "employee_name": r"^Employee Name:\s*(.+)$",
    "employee_id": r"^Employee ID:\s*(.+)$",
    "department": r"^Department:\s*(.+)$",
    "phone_extension": r"^Phone Extension:\s*(.+)$",
    "equipment_description": r"^Equipment Description:\s*(.+)$",
    "asset_tag": r"^Asset Tag:\s*(.+)$",
    "serial_number": r"^Serial Number:\s*(.+)$",
    "checkout_date": r"^Checkout Date:\s*(.+)$",
    "due_date": r"^Due Date:\s*(.+)$",
    "primary_use": r"^Primary Use:\s*(.+)$",
    "approving_supervisor": r"^Approving Supervisor:\s*(.+)$",
}

CHECKBOX_PATTERNS = {
    "accessory_charger": r"^- Charger:\s*(Yes|No)$",
    "accessory_tripod": r"^- Tripod:\s*(Yes|No)$",
    "accessory_case": r"^- Carrying Case:\s*(Yes|No)$",
    "inspected_operational": r"^- Equipment inspected and operational:\s*(Yes|No)$",
    "safety_briefing_completed": r"^- Safety briefing completed:\s*(Yes|No)$",
}

full_text = "\n".join(page.extract_text() or "" for page in PdfReader(REQUEST_PATH).pages)


def extract_value(pattern):
    match = re.search(pattern, full_text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find pattern: {pattern}")
    return match.group(1).strip()


text_values = {field_id: extract_value(pattern) for field_id, pattern in TEXT_PATTERNS.items()}
checkbox_values = {
    field_id: extract_value(pattern) == "Yes"
    for field_id, pattern in CHECKBOX_PATTERNS.items()
}

subprocess.run(["python3", EXTRACT_SCRIPT, FORM_PATH, str(FIELD_INFO_PATH)], check=True)

with open(FIELD_INFO_PATH, "r", encoding="utf-8") as handle:
    field_info = json.load(handle)

field_info_by_id = {field["field_id"]: field for field in field_info}
field_values = []

for field_id, value in text_values.items():
    info = field_info_by_id[field_id]
    field_values.append(
        {
            "field_id": field_id,
            "description": field_id.replace("_", " "),
            "page": info["page"],
            "value": value,
        }
    )

for field_id, should_check in checkbox_values.items():
    info = field_info_by_id[field_id]
    field_values.append(
        {
            "field_id": field_id,
            "description": field_id.replace("_", " "),
            "page": info["page"],
            "value": info["checked_value"] if should_check else info["unchecked_value"],
        }
    )

with open(FIELD_VALUES_PATH, "w", encoding="utf-8") as handle:
    json.dump(field_values, handle, indent=2)
    handle.write("\n")

subprocess.run(
    ["python3", FILL_SCRIPT, FORM_PATH, str(FIELD_VALUES_PATH), OUTPUT_PATH],
    check=True,
)
PY
