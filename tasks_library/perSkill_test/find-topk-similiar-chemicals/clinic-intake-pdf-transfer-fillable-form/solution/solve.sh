#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace/tmp

skill_scripts="/root/.codex/skills/pdf/scripts"
input_form="/root/data/clinic_intake_form"
patient_json="/root/data/patient_payload.json"
field_info_json="/root/workspace/tmp/field_info.json"
field_values_json="/root/workspace/tmp/field_values.json"
output_form="/root/workspace/completed_intake.pdf"

python3 "$skill_scripts/extract_form_field_info.py" "$input_form" "$field_info_json"

python3 - <<'PY'
import json
from pathlib import Path

patient = json.loads(Path("/root/data/patient_payload.json").read_text(encoding="utf-8"))["patient"]
field_info = json.loads(Path("/root/workspace/tmp/field_info.json").read_text(encoding="utf-8"))
fields_by_id = {field["field_id"]: field for field in field_info}

visit_map = {
    "new_patient": "/NewPatient",
    "follow_up": "/FollowUp",
}


def checkbox_value(field_id: str, enabled: bool) -> str:
    field = fields_by_id[field_id]
    return field["checked_value"] if enabled else field["unchecked_value"]


field_values = [
    {
        "field_id": "pt_last_name",
        "description": "Patient last name",
        "page": fields_by_id["pt_last_name"]["page"],
        "value": patient["legal_name"]["last"],
    },
    {
        "field_id": "pt_first_name",
        "description": "Preferred first name",
        "page": fields_by_id["pt_first_name"]["page"],
        "value": patient["legal_name"]["first"],
    },
    {
        "field_id": "pt_birth_date",
        "description": "Date of birth",
        "page": fields_by_id["pt_birth_date"]["page"],
        "value": patient["birth_date"],
    },
    {
        "field_id": "pt_mobile_phone",
        "description": "Mobile phone",
        "page": fields_by_id["pt_mobile_phone"]["page"],
        "value": patient["contact"]["mobile"],
    },
    {
        "field_id": "pt_allergies",
        "description": "Known allergies",
        "page": fields_by_id["pt_allergies"]["page"],
        "value": patient["clinical_flags"]["allergies"],
    },
    {
        "field_id": "visit_type",
        "description": "Visit type radio group",
        "page": fields_by_id["visit_type"]["page"],
        "value": visit_map[patient["appointment"]["track"]],
    },
    {
        "field_id": "cb_sms",
        "description": "Text appointment reminders checkbox",
        "page": fields_by_id["cb_sms"]["page"],
        "value": checkbox_value("cb_sms", patient["preferences"]["sms_reminders"]),
    },
    {
        "field_id": "cb_privacy",
        "description": "Received privacy notice checkbox",
        "page": fields_by_id["cb_privacy"]["page"],
        "value": checkbox_value("cb_privacy", patient["acknowledgements"]["privacy_notice_received"]),
    },
]

Path("/root/workspace/tmp/field_values.json").write_text(
    json.dumps(field_values, indent=2),
    encoding="utf-8",
)
PY

python3 "$skill_scripts/fill_fillable_fields.py" "$input_form" "$field_values_json" "$output_form"
