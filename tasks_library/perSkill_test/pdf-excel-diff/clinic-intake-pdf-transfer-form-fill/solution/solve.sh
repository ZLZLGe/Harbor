#!/bin/bash
set -euo pipefail

python3 /root/.codex/skills/pdf/scripts/extract_form_field_info.py \
  /root/clinic_intake_form.pdf \
  /tmp/clinic_field_info.json

python3 - <<'PY'
import json
import re
from pathlib import Path


PATIENT_FILE = Path("/root/patient_profile.json")
NOTE_FILE = Path("/root/visit_note.txt")
FIELD_INFO_FILE = Path("/tmp/clinic_field_info.json")
FIELD_VALUES_FILE = Path("/tmp/clinic_field_values.json")


patient_payload = json.loads(PATIENT_FILE.read_text(encoding="utf-8"))
note_text = NOTE_FILE.read_text(encoding="utf-8")
field_info = json.loads(FIELD_INFO_FILE.read_text(encoding="utf-8"))
field_by_id = {field["field_id"]: field for field in field_info}


def require(pattern):
    match = re.search(pattern, note_text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find pattern: {pattern}")
    return match.group(1).strip()


patient = patient_payload["patient"]
emergency_contact = patient_payload["emergency_contact"]
insurance = patient_payload["insurance"]
preferences = patient_payload["admission_preferences"]

text_values = {
    "patient_name": f'{patient["given_name"]} {patient["family_name"]}',
    "date_of_birth": patient["date_of_birth"],
    "medical_record_number": patient["medical_record_number"],
    "admission_date": require(r"Admission date:\s*(.+)"),
    "room_number": require(r"Assigned room:\s*(.+)"),
    "attending_physician": require(r"Attending physician:\s*(.+)"),
    "chief_complaint": patient["chief_complaint"],
    "allergies": "; ".join(patient["allergies"]),
    "current_medications": "; ".join(patient["current_medications"]),
    "preferred_language": patient["preferred_language"],
    "code_status": preferences["code_status"],
    "insurance_provider": insurance["provider"],
    "policy_number": insurance["policy_number"],
    "emergency_contact_name": emergency_contact["name"],
    "emergency_contact_phone": emergency_contact["phone"],
}

checkbox_values = {
    "interpreter_required": "Interpreter requested" in note_text,
    "droplet_isolation": "droplet isolation" in note_text.lower(),
    "fall_risk": "fall risk" in note_text.lower(),
}

field_values = []
for field_id, value in text_values.items():
    field = field_by_id[field_id]
    field_values.append(
        {
            "field_id": field_id,
            "description": field_id.replace("_", " "),
            "page": field["page"],
            "value": value,
        }
    )

for field_id, should_check in checkbox_values.items():
    field = field_by_id[field_id]
    field_values.append(
        {
            "field_id": field_id,
            "description": field_id.replace("_", " "),
            "page": field["page"],
            "value": field["checked_value"] if should_check else field["unchecked_value"],
        }
    )

FIELD_VALUES_FILE.write_text(json.dumps(field_values, indent=2), encoding="utf-8")
PY

python3 /root/.codex/skills/pdf/scripts/fill_fillable_fields.py \
  /root/clinic_intake_form.pdf \
  /tmp/clinic_field_values.json \
  /root/completed_intake_form.pdf
