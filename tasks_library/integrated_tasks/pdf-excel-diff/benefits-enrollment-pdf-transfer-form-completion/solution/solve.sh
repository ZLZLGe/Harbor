#!/bin/bash
set -euo pipefail

SCRIPT_DIR="/root/.codex/skills/pdf/scripts"
INPUT_PDF="/root/benefits_enrollment_packet.pdf"
PROFILE_JSON="/root/employee_profile.json"
FIELD_INFO="/tmp/benefits_field_info.json"
FIELD_VALUES="/tmp/benefits_field_values.json"
OUTPUT_PDF="/root/completed_benefits_enrollment.pdf"

python3 "${SCRIPT_DIR}/check_fillable_fields.py" "${INPUT_PDF}"
python3 "${SCRIPT_DIR}/extract_form_field_info.py" "${INPUT_PDF}" "${FIELD_INFO}"

python3 - <<'PY'
import json
from pathlib import Path

profile = json.loads(Path("/root/employee_profile.json").read_text())
field_info = json.loads(Path("/tmp/benefits_field_info.json").read_text())
info_by_id = {field["field_id"]: field for field in field_info}


def normalize_token(value):
    return str(value).lstrip("/")


def radio_value(field_id, desired_token):
    field = info_by_id[field_id]
    for option in field["radio_options"]:
        if normalize_token(option["value"]) == desired_token:
            return option["value"]
    raise ValueError(f"Could not resolve radio value for {field_id}: {desired_token}")


def checkbox_value(field_id, checked):
    field = info_by_id[field_id]
    return field["checked_value"] if checked else field["unchecked_value"]


employee = profile["employee"]
address = employee["address"]
elections = profile["elections"]
dependents = profile["dependents"]
signature = profile["signature"]

medical_map = {
    "Bronze HSA": "bronze",
    "PPO Plus": "ppo",
    "EPO Saver": "epo",
}
coverage_map = {
    "Employee Only": "employee_only",
    "Employee + Spouse": "employee_spouse",
    "Family": "family",
}
dental_map = {
    "Basic Dental": "basic",
    "Enhanced Dental": "enhanced",
    "Waive Dental": "waive",
}
tobacco_token = "yes" if elections["tobacco_user"] else "no"

values = [
    {"field_id": "worker_full", "page": info_by_id["worker_full"]["page"], "description": "Employee full name", "value": f'{employee["first_name"]} {employee["last_name"]}'},
    {"field_id": "worker_id", "page": info_by_id["worker_id"]["page"], "description": "Employee ID", "value": employee["employee_id"]},
    {"field_id": "org_unit", "page": info_by_id["org_unit"]["page"], "description": "Department", "value": employee["department"]},
    {"field_id": "mail_box", "page": info_by_id["mail_box"]["page"], "description": "Work email", "value": employee["email"]},
    {"field_id": "call_back", "page": info_by_id["call_back"]["page"], "description": "Phone number", "value": employee["phone"]},
    {
        "field_id": "street_box",
        "page": info_by_id["street_box"]["page"],
        "description": "Home address",
        "value": f'{address["street"]}, {address["city"]}, {address["state"]} {address["zip"]}',
    },
    {"field_id": "hire_box", "page": info_by_id["hire_box"]["page"], "description": "Hire date", "value": employee["hire_date"]},
    {
        "field_id": "med_plan",
        "page": info_by_id["med_plan"]["page"],
        "description": "Medical plan election",
        "value": radio_value("med_plan", medical_map[elections["medical_plan"]]),
    },
    {
        "field_id": "coverage_level",
        "page": info_by_id["coverage_level"]["page"],
        "description": "Coverage tier election",
        "value": radio_value("coverage_level", coverage_map[elections["coverage_tier"]]),
    },
    {
        "field_id": "dental_level",
        "page": info_by_id["dental_level"]["page"],
        "description": "Dental election",
        "value": radio_value("dental_level", dental_map[elections["dental_plan"]]),
    },
    {
        "field_id": "vision_opt_in",
        "page": info_by_id["vision_opt_in"]["page"],
        "description": "Vision election checkbox",
        "value": checkbox_value("vision_opt_in", elections["vision_enrolled"]),
    },
    {
        "field_id": "tobacco_state",
        "page": info_by_id["tobacco_state"]["page"],
        "description": "Tobacco use radio group",
        "value": radio_value("tobacco_state", tobacco_token),
    },
    {"field_id": "fsa_health", "page": info_by_id["fsa_health"]["page"], "description": "Healthcare FSA amount", "value": str(elections["fsa"]["healthcare"])},
    {"field_id": "fsa_family", "page": info_by_id["fsa_family"]["page"], "description": "Dependent care FSA amount", "value": str(elections["fsa"]["dependent_care"])},
    {"field_id": "sign_name", "page": info_by_id["sign_name"]["page"], "description": "Employee signature", "value": signature["name"]},
    {"field_id": "sign_date", "page": info_by_id["sign_date"]["page"], "description": "Signature date", "value": signature["date"]},
]

dependent_fields = [
    ("dep_a_name", "dep_a_relation", "dep_a_dob"),
    ("dep_b_name", "dep_b_relation", "dep_b_dob"),
]

for index, field_group in enumerate(dependent_fields):
    dependent = dependents[index] if index < len(dependents) else None
    dep_values = (
        dependent["name"] if dependent else "",
        dependent["relationship"] if dependent else "",
        dependent["date_of_birth"] if dependent else "",
    )
    for field_id, value in zip(field_group, dep_values):
        values.append(
            {
                "field_id": field_id,
                "page": info_by_id[field_id]["page"],
                "description": f"Dependent field {field_id}",
                "value": value,
            }
        )

Path("/tmp/benefits_field_values.json").write_text(json.dumps(values, indent=2) + "\n")
PY

(
  cd "${SCRIPT_DIR}"
  python3 fill_fillable_fields.py "${INPUT_PDF}" "${FIELD_VALUES}" "${OUTPUT_PDF}"
)
