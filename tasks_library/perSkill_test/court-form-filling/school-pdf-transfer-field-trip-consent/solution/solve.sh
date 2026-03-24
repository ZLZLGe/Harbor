#!/bin/bash
set -euo pipefail

cat > /tmp/fill_field_trip_form.py <<'PY'
#!/usr/bin/env python3

import tomllib

from pypdf import PdfReader, PdfWriter


INPUT_PDF = "/root/field-trip-consent-form.pdf"
INPUT_PACKET = "/root/student-registration.toml"
OUTPUT_PDF = "/root/field-trip-consent-filled.pdf"


def main():
    with open(INPUT_PACKET, "rb") as handle:
        packet = tomllib.load(handle)

    field_values = {
        "student_name": packet["student"]["name"],
        "student_id": packet["student"]["student_id"],
        "grade": packet["student"]["grade"],
        "homeroom": packet["student"]["homeroom"],
        "birth_date": packet["student"]["birth_date"],
        "trip_name": packet["trip"]["name"],
        "destination": packet["trip"]["destination"],
        "trip_date": packet["trip"]["trip_date"],
        "departure_time": packet["trip"]["departure_time"],
        "return_time": packet["trip"]["return_time"],
        "transportation": packet["trip"]["transportation"],
        "guardian_name": packet["guardian"]["name"],
        "guardian_relationship": packet["guardian"]["relationship"],
        "guardian_phone": packet["guardian"]["phone"],
        "guardian_email": packet["guardian"]["email"],
        "emergency_name": packet["emergency_contact"]["name"],
        "emergency_relationship": packet["emergency_contact"]["relationship"],
        "emergency_phone_day": packet["emergency_contact"]["phone_day"],
        "emergency_phone_evening": packet["emergency_contact"]["phone_evening"],
        "allergies": packet["health"]["allergies"],
        "medications": packet["health"]["medications"],
        "physician_name": packet["health"]["physician_name"],
        "physician_phone": packet["health"]["physician_phone"],
        "pickup_name": packet["pickup"]["authorized_adult"],
        "pickup_phone": packet["pickup"]["authorized_phone"],
        "signature_name": packet["signature"]["signer_name"],
        "signature_date": packet["signature"]["signed_on"],
    }

    authorization_pairs = {
        "medical_consent": packet["authorization"]["has_medical_consent"],
        "otc_meds": packet["authorization"]["allows_otc_medication"],
        "photo_release": packet["authorization"]["photo_release"],
        "self_carry_epipen": packet["authorization"]["self_carry_epipen"],
    }

    for prefix, enabled in authorization_pairs.items():
        selected_field = f"{prefix}_yes" if enabled else f"{prefix}_no"
        field_values[selected_field] = "/Yes"

    reader = PdfReader(INPUT_PDF)
    writer = PdfWriter()
    writer.append(reader)
    writer.set_need_appearances_writer()

    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

    with open(OUTPUT_PDF, "wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_field_trip_form.py
