#!/bin/bash

set -euo pipefail

INPUT_DIR="/app/workspace/intake_packet"
INPUT_PDF="${INPUT_DIR}/intake_form_blank.pdf"
INPUT_JSON="${INPUT_DIR}/patient_registration.json"
OUTPUT_PDF="/app/workspace/patient_intake_completed.pdf"
SCRIPTS_DIR="/root/.codex/skills/pdf/scripts"
FIELD_INFO_JSON="/tmp/intake_field_info.json"
FIELD_VALUES_JSON="/tmp/intake_field_values.json"

python3 "${SCRIPTS_DIR}/check_fillable_fields.py" "${INPUT_PDF}"
python3 "${SCRIPTS_DIR}/extract_form_field_info.py" "${INPUT_PDF}" "${FIELD_INFO_JSON}"

python3 - <<'PY'
import json

field_info_path = "/tmp/intake_field_info.json"
input_json_path = "/app/workspace/intake_packet/patient_registration.json"
output_json_path = "/tmp/intake_field_values.json"

with open(field_info_path, "r", encoding="utf-8") as handle:
    field_info = json.load(handle)

with open(input_json_path, "r", encoding="utf-8") as handle:
    registration = json.load(handle)

fields_by_id = {item["field_id"]: item for item in field_info}


def checkbox_value(field_id: str, selected: bool) -> str:
    field = fields_by_id[field_id]
    return field["checked_value"] if selected else field["unchecked_value"]


def entry(field_id: str, value: str):
    field = fields_by_id[field_id]
    return {
        "field_id": field_id,
        "description": field_id.replace("_", " "),
        "page": field["page"],
        "value": value,
    }


payload = [
    entry("patient_last_name", registration["patient"]["last_name"]),
    entry("patient_first_name", registration["patient"]["first_name"]),
    entry("date_of_birth", registration["patient"]["date_of_birth"]),
    entry("medical_record_number", registration["patient"]["medical_record_number"]),
    entry("preferred_language", registration["patient"]["preferred_language"]),
    entry("admission_type", registration["patient"]["admission_type"]),
    entry("interpreter_required", checkbox_value("interpreter_required", registration["screening"]["interpreter_required"])),
    entry("fall_risk_flag", checkbox_value("fall_risk_flag", registration["screening"]["fall_risk_flag"])),
    entry("insurance_provider", registration["insurance"]["provider"]),
    entry("policy_number", registration["insurance"]["policy_number"]),
    entry("primary_physician", registration["clinical"]["primary_physician"]),
    entry("known_allergies", registration["clinical"]["known_allergies"]),
    entry("emergency_contact_name", registration["emergency_contact"]["name"]),
    entry("emergency_contact_phone", registration["emergency_contact"]["phone"]),
    entry("privacy_notice_ack", checkbox_value("privacy_notice_ack", registration["acknowledgements"]["privacy_notice_ack"])),
    entry("treatment_consent_ack", checkbox_value("treatment_consent_ack", registration["acknowledgements"]["treatment_consent_ack"])),
]

with open(output_json_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
PY

python3 "${SCRIPTS_DIR}/fill_fillable_fields.py" "${INPUT_PDF}" "${FIELD_VALUES_JSON}" "${OUTPUT_PDF}"
