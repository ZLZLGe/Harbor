import os

from pypdf import PdfReader


OUTPUT_FILE = "/app/workspace/patient_intake_completed.pdf"

EXPECTED_VALUES = {
    "patient_last_name": "Nguyen",
    "patient_first_name": "Mina",
    "date_of_birth": "1986-11-02",
    "medical_record_number": "MRN-483920",
    "preferred_language": "Mandarin",
    "admission_type": "Urgent",
    "interpreter_required": "/Yes",
    "fall_risk_flag": "/Yes",
    "insurance_provider": "North Harbor Health Plan",
    "policy_number": "NH-7781-2045",
    "primary_physician": "Dr. Alia Brooks",
    "known_allergies": "Penicillin; shellfish",
    "emergency_contact_name": "David Nguyen",
    "emergency_contact_phone": "617-555-0142",
    "privacy_notice_ack": "/Yes",
    "treatment_consent_ack": "/Yes",
}


def normalize_pdf_value(value):
    if value is None:
        return ""
    return str(value)


def test_output_exists():
    assert os.path.exists(OUTPUT_FILE), "patient_intake_completed.pdf not found at /app/workspace"


def test_pdf_structure_and_field_values():
    reader = PdfReader(OUTPUT_FILE)
    assert len(reader.pages) == 2, f"Expected a 2-page PDF, got {len(reader.pages)} page(s)"

    fields = reader.get_fields()
    assert fields is not None, "Output PDF does not expose form fields"

    actual_field_names = sorted(fields.keys())
    expected_field_names = sorted(EXPECTED_VALUES.keys())
    assert actual_field_names == expected_field_names, (
        "Form field set mismatch.\n"
        f"Actual: {actual_field_names}\n"
        f"Expected: {expected_field_names}"
    )

    actual_values = {
        field_name: normalize_pdf_value(fields[field_name].get("/V"))
        for field_name in expected_field_names
    }

    assert actual_values == EXPECTED_VALUES, (
        "Filled field values do not match the registration data.\n"
        f"Actual: {actual_values}\n"
        f"Expected: {EXPECTED_VALUES}"
    )
