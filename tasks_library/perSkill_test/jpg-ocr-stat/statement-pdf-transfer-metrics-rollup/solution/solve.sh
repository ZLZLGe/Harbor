#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import json
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


SOURCE_DIR = Path("/app/workspace/monthly_statements")
OUTPUT_FILE = Path("/app/workspace/statement_metrics.json")


FIELD_PATTERNS = {
    "statement_id": [
        r"Statement ID:\s*(\S+)",
        r"Statement Ref:\s*(\S+)",
        r"Statement Number:\s*(\S+)",
    ],
    "account_id": [
        r"Account ID:\s*(\S+)",
        r"Account:\s*(\S+)",
        r"Account Number:\s*(\S+)",
    ],
    "period_start": [
        r"Period Start:\s*(\d{4}-\d{2}-\d{2})",
        r"Coverage Start:\s*(\d{4}-\d{2}-\d{2})",
        r"From:\s*(\d{4}-\d{2}-\d{2})",
        r"Service Window Start:\s*(\d{4}-\d{2}-\d{2})",
    ],
    "period_end": [
        r"Period End:\s*(\d{4}-\d{2}-\d{2})",
        r"Coverage End:\s*(\d{4}-\d{2}-\d{2})",
        r"To:\s*(\d{4}-\d{2}-\d{2})",
        r"Service Window End:\s*(\d{4}-\d{2}-\d{2})",
    ],
    "total_due": [
        r"Total Due:\s*\$?(\d+\.\d{2})",
        r"Amount Due:\s*\$?(\d+\.\d{2})",
        r"Balance Due:\s*\$?(\d+\.\d{2})",
    ],
}

ROW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+([A-Z_]+)\s+(.+?)\s+(\d+\.\d{2})$")


def extract_text(pdf_path: Path) -> str:
    raw = pdf_path.read_bytes()
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\n?endstream", raw, re.S):
        stream = match.group(1)
        if b"BT" not in stream:
            continue
        for text_match in re.finditer(rb"\((?:\\.|[^\\)])*\)\s*Tj", stream):
            literal = text_match.group(0).rsplit(b")", 1)[0][1:]
            decoded = (
                literal.replace(b"\\(", b"(")
                .replace(b"\\)", b")")
                .replace(b"\\\\", b"\\")
                .decode("latin-1")
            )
            chunks.append(decoded)
    return "\n".join(chunks)


def find_field(text: str, field_name: str) -> str:
    for pattern in FIELD_PATTERNS[field_name]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    raise ValueError(f"Missing field {field_name}")


def decimal_str(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


pdf_files = sorted(SOURCE_DIR.glob("*.pdf"))
if not pdf_files:
    raise SystemExit("No PDF files found")

statements = []
account_ids = set()
fee_counts_by_code: dict[str, int] = defaultdict(int)
fee_totals_by_code: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
monthly_totals = []
statements_with_late_fee = []

for pdf_path in pdf_files:
    text = extract_text(pdf_path)
    account_id = find_field(text, "account_id")
    account_ids.add(account_id)

    info = {
        "statement_id": find_field(text, "statement_id"),
        "period_start": find_field(text, "period_start"),
        "period_end": find_field(text, "period_end"),
        "total_due": find_field(text, "total_due"),
    }

    fee_rows = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = ROW_RE.match(line)
        if not match:
            continue
        fee_code = match.group(2)
        amount = Decimal(match.group(4))
        fee_rows.append((fee_code, amount))
        fee_counts_by_code[fee_code] += 1
        fee_totals_by_code[fee_code] += amount

    if not fee_rows:
        raise ValueError(f"No fee rows found in {pdf_path.name}")

    largest_code, largest_amount = max(fee_rows, key=lambda item: (item[1], item[0]))
    total_due_decimal = Decimal(info["total_due"])
    statements.append(
        {
            "filename": pdf_path.name,
            "statement_id": info["statement_id"],
            "period_start": info["period_start"],
            "period_end": info["period_end"],
            "total_due": decimal_str(total_due_decimal),
            "fee_count": len(fee_rows),
            "largest_fee": {
                "fee_code": largest_code,
                "amount": decimal_str(largest_amount),
            },
        }
    )
    monthly_totals.append(
        {
            "month": info["period_start"][:7],
            "total_due": decimal_str(total_due_decimal),
            "fee_count": len(fee_rows),
        }
    )
    if any(fee_code == "LATE_FEE" for fee_code, _ in fee_rows):
        statements_with_late_fee.append(pdf_path.name)

if len(account_ids) != 1:
    raise ValueError(f"Expected a single account id, got {sorted(account_ids)}")

grand_total_due = sum((Decimal(item["total_due"]) for item in statements), Decimal("0.00"))
average_total_due = grand_total_due / Decimal(len(statements))
highest_statement = max(statements, key=lambda item: (Decimal(item["total_due"]), item["filename"]))

payload = {
    "source_dir": str(SOURCE_DIR),
    "statement_count": len(statements),
    "account_id": next(iter(account_ids)),
    "statements": statements,
    "rollups": {
        "grand_total_due": decimal_str(grand_total_due),
        "average_statement_total_due": decimal_str(average_total_due),
        "fee_counts_by_code": dict(sorted(fee_counts_by_code.items())),
        "fee_totals_by_code": {
            key: decimal_str(value)
            for key, value in sorted(fee_totals_by_code.items())
        },
        "monthly_totals": sorted(monthly_totals, key=lambda item: item["month"]),
        "highest_total_due_statement": {
            "filename": highest_statement["filename"],
            "statement_id": highest_statement["statement_id"],
            "total_due": highest_statement["total_due"],
        },
        "statements_with_late_fee": sorted(statements_with_late_fee),
    },
}

OUTPUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
