#!/bin/bash
set -euo pipefail

cat > /tmp/solve_expense_policy_exceptions.py <<'PY'
#!/usr/bin/env python3
import json
from collections import defaultdict

import pdfplumber

INPUT_FILE = "/root/expense_review_packet"
OUTPUT_FILE = "/root/expense_policy_exceptions.json"

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}

POLICY_HEADER = ["Category", "Limit Amount", "Rule"]
CLAIM_HEADER = ["Claim ID", "Employee ID", "Employee Name", "Category", "Claim Amount"]


def clean_row(row):
    return [str(cell).strip() if cell is not None else "" for cell in row]


def parse_int(value):
    return int(str(value).replace(",", "").replace("$", "").strip())


policy_limits = {}
claims = []

with pdfplumber.open(INPUT_FILE) as pdf:
    for page in pdf.pages:
        for table in page.extract_tables(TABLE_SETTINGS):
            if not table:
                continue

            rows = [clean_row(row) for row in table if row and any(cell is not None and str(cell).strip() for cell in row)]
            if not rows:
                continue

            header = rows[0]
            data_rows = rows[1:] if header == POLICY_HEADER or header == CLAIM_HEADER else rows

            if header == POLICY_HEADER:
                for row in data_rows:
                    if len(row) < 2 or not row[0]:
                        continue
                    policy_limits[row[0]] = parse_int(row[1])
                continue

            candidate_rows = []
            if header == CLAIM_HEADER:
                candidate_rows = data_rows
            else:
                for row in rows:
                    if len(row) >= 5 and row[0].startswith("CLM-"):
                        candidate_rows.append(row)

            for row in candidate_rows:
                if len(row) < 5 or not row[1] or not row[3]:
                    continue
                claims.append(
                    {
                        "employee_id": row[1],
                        "employee_name": row[2],
                        "category": row[3],
                        "claim_amount": parse_int(row[4]),
                    }
                )

grouped = defaultdict(lambda: {"employee_name": "", "amounts": []})
for claim in claims:
    key = (claim["employee_id"], claim["category"])
    grouped[key]["employee_name"] = claim["employee_name"]
    grouped[key]["amounts"].append(claim["claim_amount"])

exceptions = []
for (employee_id, category), value in grouped.items():
    if category not in policy_limits:
        continue

    claimed_amount = sum(value["amounts"])
    limit_amount = policy_limits[category]
    if claimed_amount <= limit_amount:
        continue

    reason = (
        "single claim exceeds category cap"
        if max(value["amounts"]) > limit_amount
        else "combined claims exceed category cap"
    )
    exceptions.append(
        {
            "employee_id": employee_id,
            "employee_name": value["employee_name"],
            "category": category,
            "claimed_amount": claimed_amount,
            "limit_amount": limit_amount,
            "exception_reason": reason,
        }
    )

exceptions.sort(key=lambda item: (item["employee_id"], item["category"]))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(exceptions, f, indent=2)
    f.write("\n")
PY

python3 /tmp/solve_expense_policy_exceptions.py
