import json
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader


OUTPUT_PATH = Path("/root/enrollment_field_values.json")
PDF_PATH = Path("/root/enrollment/forms/employee_enrollment_form")
PROFILE_PATH = Path("/root/enrollment/intake_profile.json")
EXTRACT_SCRIPT = Path("/root/.codex/skills/pdf/scripts/extract_form_field_info.py")
FILL_SCRIPT = Path("/root/.codex/skills/pdf/scripts/fill_fillable_fields.py")


def load_field_info():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_json = Path(tmp_dir) / "field_info.json"
        result = subprocess.run(
            [sys.executable, str(EXTRACT_SCRIPT), str(PDF_PATH), str(tmp_json)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        return json.loads(tmp_json.read_text(encoding="utf-8"))


def build_expected_values(field_info, profile):
    fields_by_id = {field["field_id"]: field for field in field_info}

    plan_value = None
    for option in fields_by_id["plan.code_sel"]["choice_options"]:
        if option["text"] == profile["coverage"]["medical_plan_display"]:
            plan_value = option["value"]
            break
    assert plan_value is not None

    radio_options = sorted(fields_by_id["cov.tier_rg"]["radio_options"], key=lambda item: item["rect"][0])
    tier_index = {
        "employee_only": 0,
        "employee_plus_spouse": 1,
        "family": 2,
    }[profile["coverage"]["tier"]]

    return {
        "subscr.ln": profile["employee"]["last_name"],
        "subscr.fn": profile["employee"]["first_name"],
        "member.id_4a": profile["employee"]["member_id"],
        "demog.dob": profile["employee"]["date_of_birth"],
        "contact.sms": profile["employee"]["mobile_phone"],
        "plan.code_sel": plan_value,
        "cov.tier_rg": radio_options[tier_index]["value"],
        "dep.spouse_nm": profile["household"]["spouse_name"],
        "decl.sp_tob": fields_by_id["decl.sp_tob"]["checked_value"],
        "prefs.paper_eob": fields_by_id["prefs.paper_eob"]["unchecked_value"],
        "eff.dt": profile["coverage"]["effective_date"],
    }


def load_payload():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list), "Output must be a JSON array"
    return payload


def test_output_covers_all_fillable_fields():
    payload = load_payload()
    field_info = load_field_info()

    expected_ids = {field["field_id"] for field in field_info}
    actual_ids = [item.get("field_id") for item in payload]

    assert len(payload) == len(field_info), "Output must contain exactly one entry per fillable field"
    assert len(actual_ids) == len(set(actual_ids)), "field_id values must be unique"
    assert set(actual_ids) == expected_ids

    pages_by_id = {field["field_id"]: field["page"] for field in field_info}
    for item in payload:
        assert isinstance(item.get("description"), str) and item["description"].strip()
        assert item.get("page") == pages_by_id[item["field_id"]]
        assert "value" in item


def test_values_match_profile_and_field_constraints():
    payload = load_payload()
    field_info = load_field_info()
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    expected_values = build_expected_values(field_info, profile)

    payload_by_id = {item["field_id"]: item for item in payload}
    for field_id, expected_value in expected_values.items():
        assert payload_by_id[field_id]["value"] == expected_value


def test_json_can_fill_pdf_and_round_trip_values():
    field_info = load_field_info()
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    expected_values = build_expected_values(field_info, profile)

    with tempfile.TemporaryDirectory() as tmp_dir:
        filled_pdf = Path(tmp_dir) / "filled.pdf"
        result = subprocess.run(
            [sys.executable, str(FILL_SCRIPT), str(PDF_PATH), str(OUTPUT_PATH), str(filled_pdf)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert filled_pdf.exists()

        fields = PdfReader(str(filled_pdf)).get_fields()
        for field_id, expected_value in expected_values.items():
            actual_value = fields[field_id].get("/V")
            assert str(actual_value) == str(expected_value)
