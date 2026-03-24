#!/usr/bin/env python3

import csv
import os
import re
import sys

OUTPUT_PATH = "/root/workspace/invoice_ledger.csv"
EXPECTED_ROWS = [
    {
        "invoice_no": "INV-1039",
        "vendor": "Cedar Valley Paper Co.",
        "due_date": "2026-03-30",
        "amount": "315.20",
    },
    {
        "invoice_no": "INV-1044",
        "vendor": "Apex Office Furnishings",
        "due_date": "2026-04-05",
        "amount": "2100.00",
    },
    {
        "invoice_no": "INV-1048",
        "vendor": "Northwind Industrial Supply",
        "due_date": "2026-04-15",
        "amount": "1240.00",
    },
    {
        "invoice_no": "INV-1049",
        "vendor": "Northwind Industrial Supply",
        "due_date": "2026-04-15",
        "amount": "620.00",
    },
    {
        "invoice_no": "INV-1052",
        "vendor": "Blue Harbor Logistics",
        "due_date": "2026-04-20",
        "amount": "845.50",
    },
    {
        "invoice_no": "INV-1055",
        "vendor": "Helios Lab Equipment",
        "due_date": "2026-05-01",
        "amount": "3410.75",
    },
    {
        "invoice_no": "INV-1061",
        "vendor": "Summit Safety Systems",
        "due_date": "2026-05-12",
        "amount": "980.00",
    },
]


def fail(message):
    raise AssertionError(message)


def main():
    if not os.path.exists(OUTPUT_PATH):
        fail(f"missing output file: {OUTPUT_PATH}")

    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected_header = ["invoice_no", "vendor", "due_date", "amount"]
    if not rows:
        fail("output CSV is empty")
    if rows and list(rows[0].keys()) != expected_header:
        fail(f"unexpected CSV header: {list(rows[0].keys())}")

    if rows != EXPECTED_ROWS:
        fail(f"rows mismatch: expected {EXPECTED_ROWS}, got {rows}")

    invoice_nos = [row["invoice_no"] for row in rows]
    if len(invoice_nos) != len(set(invoice_nos)):
        fail("duplicate invoice numbers remain in output")

    for row in rows:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["due_date"]):
            fail(f"due_date is not normalized: {row['due_date']}")
        if not re.fullmatch(r"\d+\.\d{2}", row["amount"]):
            fail(f"amount is not normalized: {row['amount']}")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write("1.0\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        os.makedirs("/logs/verifier", exist_ok=True)
        with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
            handle.write("0.0\n")
        print(str(exc), file=sys.stderr)
        sys.exit(1)
