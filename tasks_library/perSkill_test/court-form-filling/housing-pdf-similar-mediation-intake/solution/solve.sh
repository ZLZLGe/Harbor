#!/bin/bash
set -euo pipefail

cat > /tmp/fill_housing_form.py <<'PY'
#!/usr/bin/env python3

from pypdf import PdfReader, PdfWriter

INPUT_PDF = "/root/housing-mediation-intake.pdf"
OUTPUT_PDF = "/root/housing-mediation-filled.pdf"


FIELD_VALUES = {
    "applicant_name": "Marisol Vega",
    "applicant_address": "1489 Willow Bend Apt 3",
    "applicant_city": "Oakland",
    "applicant_state": "CA",
    "applicant_zip": "94607",
    "applicant_phone": "5105550182",
    "applicant_email": "marisol.vega@example.com",
    "respondent_name": "Daniel Kim",
    "respondent_phone": "5105550199",
    "rental_address": "2218 Lakeshore Blvd Unit B",
    "rental_city": "Oakland",
    "rental_state": "CA",
    "rental_zip": "94610",
    "lease_start": "2024-06-01",
    "move_out_date": "2026-02-14",
    "deposit_paid": "2400",
    "amount_already_returned": "600",
    "amount_requested": "1800",
    "dispute_start": "2026-02-14",
    "dispute_end": "2026-03-03",
    "prior_attempts": "Email 2026-02-20; certified letter 2026-02-27.",
    "availability": "Weekday evenings.",
    "requested_outcome": "Refund remaining $1800 deposit and explain deductions in writing.",
    "signature_name": "Marisol Vega",
    "signature_date": "2026-03-05",
    "applicant_role_tenant": "/Yes",
    "respondent_role_landlord": "/Yes",
    "issue_security_deposit": "/Yes",
    "preferred_contact_email": "/Yes",
}


def main():
    reader = PdfReader(INPUT_PDF)
    writer = PdfWriter()
    writer.append(reader)
    writer.set_need_appearances_writer()

    for page in writer.pages:
        writer.update_page_form_field_values(page, FIELD_VALUES, auto_regenerate=False)

    with open(OUTPUT_PDF, "wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_housing_form.py
