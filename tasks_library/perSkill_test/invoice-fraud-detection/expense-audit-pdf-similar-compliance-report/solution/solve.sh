#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import re

import pdfplumber


def normalize_spaces(value):
    return " ".join(value.split())


def normalize_name(value):
    return normalize_spaces(value).lower()


def normalize_city(value):
    return value.strip().lower()


def parse_page(text):
    patterns = {
        "employee_name": r"^Employee:[ \t]*(.+)$",
        "travel_city": r"^Destination City:[ \t]*(.+)$",
        "approval_code": r"^Authorization Ref:[ \t]*(.*)$",
        "reimbursement_amount": r"^Requested Amount:[ \t]*USD[ \t]*([0-9]+\.[0-9]{2})$",
        "payout_account": r"^Payout Account:[ \t]*(.+)$",
    }
    parsed = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        parsed[key] = match.group(1).strip() if match else ""
    parsed["approval_code"] = parsed["approval_code"] or None
    parsed["reimbursement_amount"] = float(parsed["reimbursement_amount"])
    return parsed


with open("/root/employee_roster.csv", newline="", encoding="utf-8") as f:
    roster_rows = list(csv.DictReader(f))

roster_by_name = {normalize_name(row["employee_name"]): row for row in roster_rows}

with open("/root/trip_approvals.json", encoding="utf-8") as f:
    approvals = {row["approval_code"]: row for row in json.load(f)}

with open("/root/policy_limits.json", encoding="utf-8") as f:
    policy_limits = json.load(f)["city_limits"]

exceptions = []

with pdfplumber.open("/root/expense_claims_bundle") as pdf:
    for index, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ""
        record = parse_page(text)

        employee = roster_by_name.get(normalize_name(record["employee_name"]))
        if employee is None:
            reason = "Unknown Employee"
        elif record["payout_account"] != employee["payout_account"]:
            reason = "Account Mismatch"
        else:
            approval = approvals.get(record["approval_code"]) if record["approval_code"] else None
            if approval is None:
                reason = "Invalid Approval"
            elif approval["employee_id"] != employee["employee_id"]:
                reason = "Employee Mismatch"
            elif normalize_city(approval["approved_city"]) != normalize_city(record["travel_city"]):
                reason = "City Mismatch"
            elif record["reimbursement_amount"] - float(policy_limits[record["travel_city"]]) > 0.01:
                reason = "Over Policy Limit"
            else:
                reason = None

        if reason:
            exceptions.append(
                {
                    "expense_page_number": index,
                    "employee_name": record["employee_name"],
                    "travel_city": record["travel_city"],
                    "approval_code": record["approval_code"],
                    "reimbursement_amount": record["reimbursement_amount"],
                    "payout_account": record["payout_account"],
                    "reason": reason,
                }
            )

with open("/root/expense_exceptions.json", "w", encoding="utf-8") as f:
    json.dump(exceptions, f, indent=2)
PY
