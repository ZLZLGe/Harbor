#!/bin/bash
set -euo pipefail

cat > /tmp/fill_app003.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import shutil

from pypdf import PdfReader, PdfWriter

INPUT_PDF = Path("/root/app003-blank.pdf")
OUTPUT_PDF = Path("/root/app003-filled.pdf")


def main() -> None:
    reader = PdfReader(str(INPUT_PDF))
    writer = PdfWriter()
    writer.append(reader)
    writer.set_need_appearances_writer(True)

    field_values = {
        "appellant.name": "Elena Marquez",
        "appellant.street": "1842 Willow Creek Drive",
        "appellant.city": "San Jose",
        "appellant.state": "CA",
        "appellant.zip": "95125",
        "appellant.phone": "4085550174",
        "appellant.email": "elena.marquez@example.com",
        "court.name": "Superior Court of California, County of Santa Clara",
        "court.branch": "Downtown Superior Court",
        "court.street": "191 N. First Street",
        "court.city_zip": "San Jose, CA 95113",
        "appeal.case_number": "",
        "case.plaintiff": "Elena Marquez",
        "case.number": "23CV418772",
        "case.defendant": "Pacific Crest Builders, Inc.",
        "notice.date_filed": "2026-02-18",
        "record.clerk_transcript": "/Yes",
        "record.appendix": "/Off",
        "record.agreed_statement": "/Off",
        "record.settled_statement": "/Off",
        "court.clerk_notes": "",
        "clerk.doc1.title": "Complaint for Negligence and Premises Liability",
        "clerk.doc1.date": "2025-06-12",
        "clerk.doc2.title": "Defendant's Motion for Summary Judgment",
        "clerk.doc2.date": "2025-11-04",
        "clerk.doc3.title": "Plaintiff's Opposition to Motion for Summary Judgment",
        "clerk.doc3.date": "2025-11-25",
        "clerk.doc4.title": "Order Granting Summary Judgment",
        "clerk.doc4.date": "2026-01-09",
        "clerk.doc5.title": "Notice of Entry of Judgment",
        "clerk.doc5.date": "2026-01-14",
        "clerk.doc6.title": "Notice of Appeal",
        "clerk.doc6.date": "2026-02-18",
        "clerk.doc7.title": "",
        "clerk.doc7.date": "",
        "clerk.additional_notes": "",
        "reporter.transcript_requested": "/Yes",
        "reporter.no_reporter_transcript": "/Off",
        "reporter.all_proceedings": "/Off",
        "reporter.selected_proceedings": "/Yes",
        "reporter.pay_estimated_cost": "/Yes",
        "reporter.fee_waiver": "/Off",
        "hearing.1.date": "2025-12-12",
        "hearing.1.description": "Hearing on defendant's motion for summary judgment",
        "hearing.1.department": "16",
        "hearing.1.reporter": "A. Kim",
        "hearing.2.date": "2026-01-09",
        "hearing.2.description": "Final ruling and entry of judgment hearing",
        "hearing.2.department": "16",
        "hearing.2.reporter": "A. Kim",
        "hearing.3.date": "",
        "hearing.3.description": "",
        "hearing.3.department": "",
        "hearing.3.reporter": "",
        "reporter.notes": "",
        "signature.name": "Elena Marquez",
        "signature.date": "2026-02-20",
        "service.name": "",
        "service.date": "",
    }

    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

    with OUTPUT_PDF.open("wb") as handle:
        writer.write(handle)

    verifier_dir = Path("/logs/verifier")
    if verifier_dir.parent.exists():
        verifier_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, verifier_dir / "app003-filled.pdf")


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_app003.py
