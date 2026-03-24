import csv
import json
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher

DATA_ROOT = os.environ.get("TASK_DATA_ROOT", "/root")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/vendor_concentration_report.json")
VENDOR_MASTER = os.path.join(DATA_ROOT, "vendor_master.csv")
CONTRACT_AWARDS = os.path.join(DATA_ROOT, "contract_awards.csv")
PAYMENT_LEDGER = os.path.join(DATA_ROOT, "payment_ledger.csv")

TARGET_DEPARTMENT = {
    "department_code": "DPT-410",
    "department_name": "Department of Water Infrastructure",
}
FOCUS_PROJECT_CATEGORY = "Stormwater Retrofit"


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_output():
    assert os.path.isfile(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE) as f:
        return json.load(f)


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def build_vendor_resolver(vendors):
    normalized_names = [normalize(row["vendor_name"]) for row in vendors]

    def resolve_vendor(raw_name):
        normalized_raw = normalize(raw_name)
        best_index, _ = max(
            enumerate(normalized_names),
            key=lambda item: SequenceMatcher(None, normalized_raw, item[1]).ratio(),
        )
        return vendors[best_index]

    return resolve_vendor


def compute_expected():
    vendors = {row["vendor_id"]: row for row in load_csv(VENDOR_MASTER)}
    vendor_rows = list(vendors.values())
    resolve_vendor = build_vendor_resolver(vendor_rows)
    awards = load_csv(CONTRACT_AWARDS)
    payments = load_csv(PAYMENT_LEDGER)

    contracts = {}
    vendor_contracts = defaultdict(set)
    vendor_awarded = defaultdict(float)
    vendor_paid = defaultdict(float)
    parent_paid = defaultdict(float)
    payments_by_contract = defaultdict(list)

    for row in awards:
        vendor = resolve_vendor(row["vendor_name_award"])
        vendor_id = vendor["vendor_id"]
        award_amount = float(row["award_amount"])
        contracts[row["contract_id"]] = {
            "contract_id": row["contract_id"],
            "department_code": row["department_code"],
            "department_name": row["department_name"],
            "project_category": row["project_category"],
            "award_amount": award_amount,
            "vendor_id": vendor_id,
            "vendor_name": vendor["vendor_name"],
            "parent_group_id": vendor["parent_group_id"],
            "parent_group_name": vendor["parent_group_name"],
        }
        if row["department_code"] == TARGET_DEPARTMENT["department_code"]:
            vendor_contracts[vendor_id].add(row["contract_id"])
            vendor_awarded[vendor_id] += award_amount

    for row in payments:
        vendor = resolve_vendor(row["payee_name_raw"])
        vendor_id = vendor["vendor_id"]
        payment = {
            "payment_id": row["payment_id"],
            "contract_id": row["contract_id"],
            "payment_date": row["payment_date"],
            "payment_amount": float(row["payment_amount"]),
            "vendor_id": vendor_id,
            "vendor_name": vendor["vendor_name"],
        }
        payments_by_contract[row["contract_id"]].append(payment)
        contract = contracts[row["contract_id"]]
        if contract["department_code"] == TARGET_DEPARTMENT["department_code"]:
            vendor_paid[vendor_id] += payment["payment_amount"]
            parent_paid[vendor["parent_group_id"]] += payment["payment_amount"]

    ranked_vendors = sorted(vendor_paid.items(), key=lambda item: (-item[1], item[0]))[:5]
    top_vendors = []
    for rank, (vendor_id, paid_amount) in enumerate(ranked_vendors, start=1):
        vendor = vendors[vendor_id]
        top_vendors.append(
            {
                "rank": rank,
                "vendor_id": vendor_id,
                "vendor_name": vendor["vendor_name"],
                "parent_group_id": vendor["parent_group_id"],
                "parent_group_name": vendor["parent_group_name"],
                "contract_count": len(vendor_contracts[vendor_id]),
                "awarded_amount": vendor_awarded[vendor_id],
                "paid_amount": paid_amount,
            }
        )

    department_total_paid = sum(parent_paid.values())
    ranked_groups = sorted(parent_paid.items(), key=lambda item: (-item[1], item[0]))
    top_group_id, top_group_paid = ranked_groups[0]
    top_group_name = next(
        vendor["parent_group_name"]
        for vendor in vendors.values()
        if vendor["parent_group_id"] == top_group_id
    )

    over_budget_payments = []
    for contract_id, contract in contracts.items():
        if contract["department_code"] != TARGET_DEPARTMENT["department_code"]:
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

    return {
        "target_department": TARGET_DEPARTMENT,
        "focus_project_category": FOCUS_PROJECT_CATEGORY,
        "top_vendors": top_vendors,
        "group_concentration": {
            "department_total_paid": department_total_paid,
            "top_group_id": top_group_id,
            "top_group_name": top_group_name,
            "top_group_paid": top_group_paid,
            "top_group_share": round(top_group_paid / department_total_paid, 6),
            "cr3": round(sum(value for _, value in ranked_groups[:3]) / department_total_paid, 6),
            "hhi": round(
                sum((value / department_total_paid) ** 2 for value in parent_paid.values()),
                6,
            ),
        },
        "over_budget_payments": over_budget_payments,
    }


def test_report_matches_expected_calculation():
    actual = load_output()
    expected = compute_expected()
    assert actual == expected


def test_schema_and_ordering():
    report = load_output()

    assert set(report.keys()) == {
        "target_department",
        "focus_project_category",
        "top_vendors",
        "group_concentration",
        "over_budget_payments",
    }

    assert report["target_department"] == TARGET_DEPARTMENT
    assert report["focus_project_category"] == FOCUS_PROJECT_CATEGORY

    top_vendors = report["top_vendors"]
    assert len(top_vendors) == 5
    assert [row["rank"] for row in top_vendors] == [1, 2, 3, 4, 5]
    assert [
        (row["paid_amount"], row["vendor_id"])
        for row in top_vendors
    ] == sorted(
        [(row["paid_amount"], row["vendor_id"]) for row in top_vendors],
        key=lambda row: (-row[0], row[1]),
    )
    for row in top_vendors:
        assert isinstance(row["contract_count"], int)
        assert isinstance(row["awarded_amount"], (int, float))
        assert isinstance(row["paid_amount"], (int, float))

    concentration = report["group_concentration"]
    assert concentration["top_group_share"] == round(
        concentration["top_group_paid"] / concentration["department_total_paid"],
        6,
    )
    assert isinstance(concentration["department_total_paid"], (int, float))
    assert isinstance(concentration["top_group_paid"], (int, float))
    assert 0 < concentration["cr3"] <= 1
    assert 0 < concentration["hhi"] <= 1

    over_budget = report["over_budget_payments"]
    assert [row["payment_id"] for row in over_budget] == [
        row["payment_id"]
        for row in sorted(over_budget, key=lambda row: (row["payment_date"], row["payment_id"]))
    ]
    for row in over_budget:
        assert row["project_category"] == FOCUS_PROJECT_CATEGORY
        assert isinstance(row["payment_amount"], (int, float))
        assert isinstance(row["award_amount"], (int, float))
        assert isinstance(row["cumulative_paid_after_payment"], (int, float))
        assert isinstance(row["over_budget_amount"], (int, float))
        assert row["cumulative_paid_after_payment"] > row["award_amount"]
        assert row["over_budget_amount"] == (
            row["cumulative_paid_after_payment"] - row["award_amount"]
        )
