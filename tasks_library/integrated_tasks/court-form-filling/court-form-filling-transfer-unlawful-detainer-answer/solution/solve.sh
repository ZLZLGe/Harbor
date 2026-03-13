#!/bin/bash
set -euo pipefail

cat > /tmp/fill_ud105.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import shutil

from pypdf import PdfReader, PdfWriter


INPUT_PDF = Path("/root/ud105-blank.pdf")
OUTPUT_PDF = Path("/root/ud105-filled.pdf")


def main() -> None:
    reader = PdfReader(str(INPUT_PDF))
    writer = PdfWriter()
    writer.append(reader)
    writer.set_need_appearances_writer(True)

    field_values = {
        "party.name": "Maya Patel",
        "party.street": "1742 Jasmine Street, Apt. 3B",
        "party.city_state_zip": "Oakland, CA 94612",
        "party.phone": "5105550187",
        "party.email": "maya.patel.renter@gmail.com",
        "court.name": "Superior Court of California, County of Alameda",
        "court.location": "Wiley W. Manuel Courthouse",
        "court.address": "661 Washington Street, Oakland, CA 94607",
        "caption.plaintiff": "Redwood Property Management, LLC",
        "caption.defendant": "Maya Patel",
        "caption.case_number": "24UD031842",
        "response.general_denial": "/Yes",
        "response.denial_facts": (
            "The 3-day notice demanded late fees and parking charges that were not rent, "
            "and the landlord accepted Maya's $2,800 partial rent payment after serving the notice."
        ),
        "defense.notice_defective": "/Yes",
        "defense.rent_accepted_after_notice": "/Yes",
        "defense.habitability": "/Yes",
        "defense.retaliation": "/Yes",
        "request.dismiss_complaint": "/Yes",
        "request.costs": "/Yes",
        "request.attorney_fees": "/Yes",
        "signature.name": "Maya Patel",
        "signature.date": "2026-02-12",
        "party.bar_number": "",
        "court.hearing_date": "",
        "court.department": "",
        "court.clerk_initials": "",
        "response.other_statements": "",
        "defense.discrimination": "/Off",
        "defense.nuisance": "/Off",
        "defense.other": "/Off",
        "defense.other_text": "",
        "request.jury_trial": "/Off",
        "request.other_relief": "",
        "signature.interpreter": "",
    }

    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

    with OUTPUT_PDF.open("wb") as handle:
        writer.write(handle)

    verifier_dir = Path("/logs/verifier")
    if verifier_dir.parent.exists():
        verifier_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, verifier_dir / "ud105-filled.pdf")


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_ud105.py
