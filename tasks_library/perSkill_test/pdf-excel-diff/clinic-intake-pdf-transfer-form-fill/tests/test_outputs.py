#!/usr/bin/env python3

import sys
from pathlib import Path

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/completed_intake_form.pdf")

EXPECTED_TEXT_VALUES = {
    "patient_name": "Mei Chen",
    "date_of_birth": "1978-11-02",
    "medical_record_number": "MRN-48291",
    "admission_date": "2026-02-18",
    "room_number": "512B",
    "attending_physician": "Alicia Gomez, MD",
    "chief_complaint": "Shortness of breath and productive cough",
    "allergies": "Penicillin (rash); Latex",
    "current_medications": "Lisinopril 10 mg daily; Metformin 500 mg twice daily",
    "preferred_language": "Cantonese",
    "code_status": "Full Code",
    "insurance_provider": "Harbor Health PPO",
    "policy_number": "HHP-7782319",
    "emergency_contact_name": "David Chen",
    "emergency_contact_phone": "555-0147",
}

EXPECTED_CHECKED_FIELDS = {
    "interpreter_required",
    "droplet_isolation",
    "fall_risk",
}


def fail(message):
    raise AssertionError(message)


def normalize_field_value(value):
    if value is None:
        return ""
    return str(value)


def main():
    if not OUTPUT_FILE.exists():
        fail(f"Output file not found: {OUTPUT_FILE}")

    reader = PdfReader(str(OUTPUT_FILE))
    fields = reader.get_fields()
    if not fields:
        fail("Output PDF does not contain readable form fields")

    for field_id, expected_value in EXPECTED_TEXT_VALUES.items():
        if field_id not in fields:
            fail(f"Missing expected field: {field_id}")
        actual_value = normalize_field_value(fields[field_id].get("/V"))
        if actual_value != expected_value:
            fail(f"Field {field_id} expected {expected_value!r} but found {actual_value!r}")

    for field_id in EXPECTED_CHECKED_FIELDS:
        if field_id not in fields:
            fail(f"Missing checkbox field: {field_id}")
        actual_value = normalize_field_value(fields[field_id].get("/V"))
        if actual_value in {"", "/Off", "Off"}:
            fail(f"Checkbox {field_id} was not checked")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"TEST FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
