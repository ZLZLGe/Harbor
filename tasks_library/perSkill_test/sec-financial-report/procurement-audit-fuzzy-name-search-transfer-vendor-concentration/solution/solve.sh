#!/bin/bash
set -euo pipefail

DATA_ROOT="${DATA_ROOT:-/root}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/vendor_concentration_report.json}"

python3 - <<'PY'
import csv
import json
import os
import re
from collections import defaultdict

DATA_ROOT = os.environ.get("DATA_ROOT", "/root")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/vendor_concentration_report.json")

TARGET_DEPARTMENT_CODE = "DPT-410"
TARGET_DEPARTMENT_NAME = "Department of Water Infrastructure"
FOCUS_PROJECT_CATEGORY = "Stormwater Retrofit"

try:
    from rapidfuzz import fuzz, process
except ImportError:
    from difflib import SequenceMatcher
    fuzz = None
    process = None


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


vendor_master = load_csv(os.path.join(DATA_ROOT, "vendor_master.csv"))
contract_awards = load_csv(os.path.join(DATA_ROOT, "contract_awards.csv"))
payment_ledger = load_csv(os.path.join(DATA_ROOT, "payment_ledger.csv"))

vendor_by_id = {row["vendor_id"]: row for row in vendor_master}
normalized_vendor_names = [normalize(row["vendor_name"]) for row in vendor_master]


def resolve_vendor(raw_name):
    normalized_raw = normalize(raw_name)
    if process is not None:
        _, _, index = process.extractOne(
            normalized_raw,
            normalized_vendor_names,
            scorer=fuzz.WRatio,
        )
        return vendor_master[index]

    best_index, _ = max(
        enumerate(normalized_vendor_names),
        key=lambda item: SequenceMatcher(None, normalized_raw, item[1]).ratio(),
    )
    return vendor_master[best_index]


contracts = {}
vendor_contracts = defaultdict(set)
vendor_awarded = defaultdict(float)
vendor_paid = defaultdict(float)
parent_paid = defaultdict(float)
payments_by_contract = defaultdict(list)

for row in contract_awards:
    vendor = resolve_vendor(row["vendor_name_award"])
    award_amount = float(row["award_amount"])
    contract = {
        "contract_id": row["contract_id"],
        "department_code": row["department_code"],
        "department_name": row["department_name"],
        "project_category": row["project_category"],
        "project_name": row["project_name"],
        "award_date": row["award_date"],
        "award_amount": award_amount,
        "vendor_id": vendor["vendor_id"],
        "vendor_name": vendor["vendor_name"],
        "parent_group_id": vendor["parent_group_id"],
        "parent_group_name": vendor["parent_group_name"],
    }
    contracts[row["contract_id"]] = contract
    if row["department_code"] == TARGET_DEPARTMENT_CODE:
        vendor_contracts[vendor["vendor_id"]].add(row["contract_id"])
        vendor_awarded[vendor["vendor_id"]] += award_amount

for row in payment_ledger:
    vendor = resolve_vendor(row["payee_name_raw"])
    amount = float(row["payment_amount"])
    payment = {
        "payment_id": row["payment_id"],
        "contract_id": row["contract_id"],
        "payment_date": row["payment_date"],
        "payment_amount": amount,
        "vendor_id": vendor["vendor_id"],
        "vendor_name": vendor["vendor_name"],
    }
    payments_by_contract[row["contract_id"]].append(payment)
    contract = contracts[row["contract_id"]]
    if contract["department_code"] == TARGET_DEPARTMENT_CODE:
        vendor_paid[vendor["vendor_id"]] += amount
        parent_paid[vendor["parent_group_id"]] += amount

top_vendors = []
for vendor_id, paid_amount in sorted(
    vendor_paid.items(),
    key=lambda item: (-item[1], item[0]),
):
    vendor = vendor_by_id[vendor_id]
    top_vendors.append(
        {
            "vendor_id": vendor_id,
            "vendor_name": vendor["vendor_name"],
            "parent_group_id": vendor["parent_group_id"],
            "parent_group_name": vendor["parent_group_name"],
            "contract_count": len(vendor_contracts[vendor_id]),
            "awarded_amount": vendor_awarded[vendor_id],
            "paid_amount": paid_amount,
        }
    )

top_vendors = top_vendors[:5]
for index, item in enumerate(top_vendors, start=1):
    item["rank"] = index

department_total_paid = sum(parent_paid.values())
ranked_groups = sorted(parent_paid.items(), key=lambda item: (-item[1], item[0]))
top_group_id, top_group_paid = ranked_groups[0]
top_group_name = next(
    row["parent_group_name"] for row in vendor_master if row["parent_group_id"] == top_group_id
)

def round6(value):
    return round(value, 6)


group_concentration = {
    "department_total_paid": department_total_paid,
    "top_group_id": top_group_id,
    "top_group_name": top_group_name,
    "top_group_paid": top_group_paid,
    "top_group_share": round6(top_group_paid / department_total_paid),
    "cr3": round6(sum(value for _, value in ranked_groups[:3]) / department_total_paid),
    "hhi": round6(sum((value / department_total_paid) ** 2 for value in parent_paid.values())),
}

over_budget_payments = []
for contract_id, contract in contracts.items():
    if contract["department_code"] != TARGET_DEPARTMENT_CODE:
        continue
    if contract["project_category"] != FOCUS_PROJECT_CATEGORY:
        continue

    cumulative = 0.0
    for payment in sorted(
        payments_by_contract[contract_id],
        key=lambda item: (item["payment_date"], item["payment_id"]),
    ):
        cumulative += payment["payment_amount"]
        if cumulative > contract["award_amount"]:
            over_budget_payments.append(
                {
                    "payment_id": payment["payment_id"],
                    "payment_date": payment["payment_date"],
                    "contract_id": contract_id,
                    "vendor_id": payment["vendor_id"],
                    "vendor_name": payment["vendor_name"],
                    "project_category": contract["project_category"],
                    "payment_amount": payment["payment_amount"],
                    "award_amount": contract["award_amount"],
                    "cumulative_paid_after_payment": cumulative,
                    "over_budget_amount": cumulative - contract["award_amount"],
                }
            )

over_budget_payments.sort(key=lambda item: (item["payment_date"], item["payment_id"]))

report = {
    "target_department": {
        "department_code": TARGET_DEPARTMENT_CODE,
        "department_name": TARGET_DEPARTMENT_NAME,
    },
    "focus_project_category": FOCUS_PROJECT_CATEGORY,
    "top_vendors": [
        {
            "rank": item["rank"],
            "vendor_id": item["vendor_id"],
            "vendor_name": item["vendor_name"],
            "parent_group_id": item["parent_group_id"],
            "parent_group_name": item["parent_group_name"],
            "contract_count": item["contract_count"],
            "awarded_amount": item["awarded_amount"],
            "paid_amount": item["paid_amount"],
        }
        for item in top_vendors
    ],
    "group_concentration": group_concentration,
    "over_budget_payments": over_budget_payments,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(report, f, indent=2)
PY
