#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

INPUT_PDF = Path("/root/vendor-statement.pdf")
OUTPUT_JSON = Path("/root/invoice-summary.json")


def extract_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        text = result.stdout.strip()
        if text:
            return text
    except Exception:
        pass

    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


text = extract_text(INPUT_PDF)
statement_match = re.search(r"Statement Date:\s*(\d{4}-\d{2}-\d{2})", text)
if not statement_match:
    raise SystemExit("Could not find statement date in vendor statement PDF.")

statement_date = statement_match.group(1)
pattern = re.compile(
    r"^(BR-\d{4})\s+\d{4}-\d{2}-\d{2}\s+(\d{4}-\d{2}-\d{2})\s+\$([0-9,]+\.\d{2})$",
    re.MULTILINE,
)

invoices = []
for invoice_number, due_date, amount_due in pattern.findall(text):
    invoices.append(
        {
            "invoice_number": invoice_number,
            "statement_date": statement_date,
            "due_date": due_date,
            "amount_due": amount_due.replace(",", ""),
        }
    )

if not invoices:
    raise SystemExit("Could not find any invoice rows in vendor statement PDF.")

invoices.sort(key=lambda item: item["invoice_number"])
OUTPUT_JSON.write_text(json.dumps({"invoices": invoices}, indent=2) + "\n")
PY
