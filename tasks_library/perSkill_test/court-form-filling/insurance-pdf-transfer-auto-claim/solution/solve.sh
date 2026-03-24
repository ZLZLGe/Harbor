#!/bin/bash
set -euo pipefail

cat > /tmp/fill_auto_claim.py <<'PY'
#!/usr/bin/env python3

import json

from pypdf import PdfReader, PdfWriter


INPUT_PDF = "/root/auto-claim-form.pdf"
INPUT_PACKET = "/root/claim-packet.json"
OUTPUT_PDF = "/root/auto-claim-filled.pdf"


def main():
    with open(INPUT_PACKET, "r", encoding="utf-8") as handle:
        packet = json.load(handle)

    field_values = {
        "policyholder_name": packet["policyholder"]["name"],
        "policy_number": packet["policyholder"]["policy_number"],
        "contact_phone": packet["policyholder"]["phone"],
        "contact_email": packet["policyholder"]["email"],
        "mailing_address": packet["policyholder"]["mailing_address"],
        "vehicle_year": packet["vehicle"]["year"],
        "vehicle_make_model": packet["vehicle"]["make_model"],
        "license_plate": packet["vehicle"]["license_plate"],
        "accident_date": packet["incident"]["date"],
        "accident_time": packet["incident"]["time"],
        "accident_location": packet["incident"]["location"],
        "accident_summary": packet["incident"]["summary"],
        "damaged_parts": packet["incident"]["damaged_parts"],
        "estimated_damage": packet["incident"]["estimated_damage_usd"],
        "signature_name": packet["signature"]["name"],
        "signature_date": packet["signature"]["date"],
    }

    checkbox_fields = {
        "single_vehicle_incident": packet["incident"]["single_vehicle_incident"],
        "insured_driver_responsible": packet["incident"]["insured_driver_responsible"],
        "vehicle_drivable": packet["incident"]["vehicle_drivable"],
        "vehicle_towed": packet["incident"]["vehicle_towed"],
        "police_report_filed": packet["incident"]["police_report_filed"],
        "injuries_reported": packet["incident"]["injuries_reported"],
    }

    for field_name, checked in checkbox_fields.items():
        if checked:
            field_values[field_name] = "/Yes"

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

python3 /tmp/fill_auto_claim.py
