import json
from pathlib import Path

from pypdf import PdfReader


OUTPUT_PATH = Path("/root/workspace/completed_intake.pdf")
PATIENT_PATH = Path("/root/data/patient_payload.json")

REQUIRED_FIELDS = {
    "pt_last_name",
    "pt_first_name",
    "pt_birth_date",
    "pt_mobile_phone",
    "pt_allergies",
    "visit_type",
    "cb_sms",
    "cb_privacy",
}


def load_fields(path: Path):
    reader = PdfReader(str(path))
    fields = reader.get_fields()
    assert fields, "输出文件必须保留可读取的表单字段"
    return fields


def field_value(fields, field_id: str):
    field = fields[field_id]
    value = field.get("/V")
    if value is None and field.get("/FT") == "/Btn":
        value = field.get("/AS")
    if value is None:
        return None
    return str(value)


def expected_values():
    patient = json.loads(PATIENT_PATH.read_text(encoding="utf-8"))["patient"]
    visit_map = {
        "new_patient": "/NewPatient",
        "follow_up": "/FollowUp",
    }
    return {
        "pt_last_name": patient["legal_name"]["last"],
        "pt_first_name": patient["legal_name"]["first"],
        "pt_birth_date": patient["birth_date"],
        "pt_mobile_phone": patient["contact"]["mobile"],
        "pt_allergies": patient["clinical_flags"]["allergies"],
        "visit_type": visit_map[patient["appointment"]["track"]],
        "cb_sms": "/Yes" if patient["preferences"]["sms_reminders"] else "/Off",
        "cb_privacy": "/Yes" if patient["acknowledgements"]["privacy_notice_received"] else "/Off",
    }


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/workspace/completed_intake.pdf"


def test_form_fields_remain_accessible():
    fields = load_fields(OUTPUT_PATH)
    assert REQUIRED_FIELDS.issubset(fields.keys()), "输出文件缺少必要表单字段"


def test_values_match_patient_payload():
    fields = load_fields(OUTPUT_PATH)
    expected = expected_values()

    for field_id, expected_value in expected.items():
        assert field_value(fields, field_id) == expected_value, f"{field_id} 的值不正确"
