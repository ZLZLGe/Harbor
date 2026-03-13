#!/bin/bash
set -euo pipefail

cat > /tmp/fill_js44.py <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import shutil

from pypdf import PdfReader, PdfWriter

INPUT_PDF = Path("/root/js44-blank.pdf")
OUTPUT_PDF = Path("/root/js44-filled.pdf")


def main() -> None:
    reader = PdfReader(str(INPUT_PDF))
    writer = PdfWriter()
    writer.append(reader)
    writer.set_need_appearances_writer(True)

    field_values = {
        "case.title": "Angela Ruiz v. Lakeshore Bistro Group, LLC",
        "plaintiff.name": "Angela Ruiz",
        "plaintiff.county": "Cook",
        "defendant.name": "Lakeshore Bistro Group, LLC",
        "defendant.county": "Cook",
        "jurisdiction_us_plaintiff": "/Off",
        "jurisdiction_us_defendant": "/Off",
        "jurisdiction_federal_question": "/Yes",
        "jurisdiction_diversity": "/Off",
        "origin_original": "/Yes",
        "origin_removed": "/Off",
        "origin_remanded": "/Off",
        "origin_reinstated": "/Off",
        "origin_transferred": "/Off",
        "origin_multidistrict": "/Off",
        "cause.statute": "29 U.S.C. § 207",
        "cause.description": "Unpaid overtime wages under the Fair Labor Standards Act.",
        "jury_yes": "/Yes",
        "jury_no": "/Off",
        "nature_110_insurance": "/Off",
        "nature_190_other_contract": "/Off",
        "nature_310_airplane": "/Off",
        "nature_442_employment": "/Off",
        "nature_710_flsa": "/Yes",
        "nature_790_other_labor": "/Off",
        "nature_820_copyright": "/Off",
        "nature_840_trademark": "/Off",
    }

    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

    with OUTPUT_PDF.open("wb") as handle:
        writer.write(handle)

    verifier_dir = Path("/logs/verifier")
    if verifier_dir.parent.exists():
        verifier_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, verifier_dir / "js44-filled.pdf")


if __name__ == "__main__":
    main()
PY

python3 /tmp/fill_js44.py
