#!/usr/bin/env python3

import json
from collections import defaultdict
from pathlib import Path

import pdfplumber

OUTPUT_FILE = Path("/root/expense_policy_exceptions.json")
INPUT_FILE = "/root/expense_review_packet"

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}

POLICY_HEADER = ["Category", "Limit Amount", "Rule"]
CLAIM_HEADER = ["Claim ID", "Employee ID", "Employee Name", "Category", "Claim Amount"]
EXPECTED_KEYS = [
    "employee_id",
    "employee_name",
    "category",
    "claimed_amount",
    "limit_amount",
    "exception_reason",
]
VALID_REASONS = {
    "single claim exceeds category cap",
    "combined claims exceed category cap",
}


def clean_row(row):
    return [str(cell).strip() if cell is not None else "" for cell in row]


def parse_int(value):
    return int(str(value).replace(",", "").replace("$", "").strip())


def parse_expected_from_pdf():
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

    expected = []
    for (employee_id, category), value in grouped.items():
        limit_amount = policy_limits[category]
        claimed_amount = sum(value["amounts"])
        if claimed_amount <= limit_amount:
            continue

        expected.append(
            {
                "employee_id": employee_id,
                "employee_name": value["employee_name"],
                "category": category,
                "claimed_amount": claimed_amount,
                "limit_amount": limit_amount,
                "exception_reason": (
                    "single claim exceeds category cap"
                    if max(value["amounts"]) > limit_amount
                    else "combined claims exceed category cap"
                ),
            }
        )

    return sorted(expected, key=lambda item: (item["employee_id"], item["category"]))


def load_output():
    with OUTPUT_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_is_json_array():
    payload = load_output()
    assert isinstance(payload, list), "Output must be a JSON array"


def test_each_record_has_exact_schema():
    payload = load_output()
    for index, item in enumerate(payload):
        assert isinstance(item, dict), f"Row {index} is not a JSON object"
        assert sorted(item.keys()) == sorted(EXPECTED_KEYS), f"Row {index} has unexpected keys: {item.keys()}"


def test_reason_values_are_valid():
    payload = load_output()
    for index, item in enumerate(payload):
        assert item["exception_reason"] in VALID_REASONS, f"Row {index} has invalid reason"


def test_amount_fields_are_integers():
    payload = load_output()
    for index, item in enumerate(payload):
        assert isinstance(item["claimed_amount"], int), f"Row {index} claimed_amount must be int"
        assert isinstance(item["limit_amount"], int), f"Row {index} limit_amount must be int"


def test_output_matches_expected_exceptions():
    actual = load_output()
    expected = parse_expected_from_pdf()
    assert actual == expected


def test_output_is_sorted():
    payload = load_output()
    assert payload == sorted(payload, key=lambda item: (item["employee_id"], item["category"]))


def test_contains_multiple_reason_types():
    payload = load_output()
    reasons = {item["exception_reason"] for item in payload}
    assert reasons == VALID_REASONS
