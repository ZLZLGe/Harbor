#!/bin/bash
set -euo pipefail

python3 /root/.codex/skills/pdf/scripts/extract_form_field_info.py \
  /root/enrollment/forms/employee_enrollment_form \
  /tmp/enrollment_field_info.json

python3 - <<'PY'
import json
from pathlib import Path


FIELD_INFO_PATH = Path("/tmp/enrollment_field_info.json")
PROFILE_PATH = Path("/root/enrollment/intake_profile.json")
OUTPUT_PATH = Path("/root/enrollment_field_values.json")


field_info = json.loads(FIELD_INFO_PATH.read_text(encoding="utf-8"))
profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
fields_by_id = {field["field_id"]: field for field in field_info}


def checkbox_value(field_id: str, checked: bool) -> str:
    field = fields_by_id[field_id]
    return field["checked_value"] if checked else field["unchecked_value"]


def radio_value(field_id: str, tier_key: str) -> str:
    field = fields_by_id[field_id]
    options = sorted(field["radio_options"], key=lambda item: item["rect"][0])
    index_map = {
        "employee_only": 0,
        "employee_plus_spouse": 1,
        "family": 2,
    }
    return options[index_map[tier_key]]["value"]


def choice_value(field_id: str, display_text: str) -> str:
    field = fields_by_id[field_id]
    for option in field["choice_options"]:
        if option["text"] == display_text:
            return option["value"]
    raise RuntimeError(f"Choice text not found for {field_id}: {display_text}")


expected_values = {
    "subscr.ln": profile["employee"]["last_name"],
    "subscr.fn": profile["employee"]["first_name"],
    "member.id_4a": profile["employee"]["member_id"],
    "demog.dob": profile["employee"]["date_of_birth"],
    "contact.sms": profile["employee"]["mobile_phone"],
    "plan.code_sel": choice_value("plan.code_sel", profile["coverage"]["medical_plan_display"]),
    "cov.tier_rg": radio_value("cov.tier_rg", profile["coverage"]["tier"]),
    "dep.spouse_nm": profile["household"]["spouse_name"],
    "decl.sp_tob": checkbox_value("decl.sp_tob", profile["household"]["spouse_uses_tobacco"]),
    "prefs.paper_eob": checkbox_value("prefs.paper_eob", profile["preferences"]["paperless_eob"]),
    "eff.dt": profile["coverage"]["effective_date"],
}


descriptions = {
    "subscr.ln": "Employee last name",
    "subscr.fn": "Employee first name",
    "member.id_4a": "Member ID",
    "demog.dob": "Employee date of birth",
    "contact.sms": "Employee mobile phone",
    "plan.code_sel": "Selected medical plan code",
    "cov.tier_rg": "Coverage tier selection",
    "dep.spouse_nm": "Covered spouse name",
    "decl.sp_tob": "Checkbox for spouse tobacco use",
    "prefs.paper_eob": "Checkbox for paperless EOB preference",
    "eff.dt": "Coverage effective date",
}


payload = []
for field in field_info:
    field_id = field["field_id"]
    payload.append(
        {
            "field_id": field_id,
            "page": field["page"],
            "description": descriptions[field_id],
            "value": expected_values[field_id],
        }
    )


OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
