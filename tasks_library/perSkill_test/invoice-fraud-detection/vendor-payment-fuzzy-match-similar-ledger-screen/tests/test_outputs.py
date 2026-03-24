import json
import os


OUTPUT_PATH = os.environ.get("PRIMARY_OUTPUT_FILE", "/root/payment_anomalies.json")

EXPECTED_ANOMALIES = [
    {
        "request_id": "REQ-002",
        "vendor_name": "Blue Harbor Supply Co.",
        "requested_amount": 9430.5,
        "bank_account": "US00-BH-000000",
        "po_number": "PO-91002",
        "reason": "Bank Account Mismatch",
    },
    {
        "request_id": "REQ-003",
        "vendor_name": "Apex Office Systems Limited",
        "requested_amount": 1275.75,
        "bank_account": "US00-AO-778899",
        "po_number": "PO-91003",
        "reason": "Amount Mismatch",
    },
    {
        "request_id": "REQ-004",
        "vendor_name": "GreenLine Facility Services",
        "requested_amount": 6500.0,
        "bank_account": "US00-GF-112233",
        "po_number": "PO-91004",
        "reason": "Vendor Mismatch",
    },
    {
        "request_id": "REQ-005",
        "vendor_name": "Everstream Logistics Incorporated",
        "requested_amount": 6500.0,
        "bank_account": "US00-EL-554433",
        "po_number": "PO-99999",
        "reason": "Invalid PO",
    },
    {
        "request_id": "REQ-006",
        "vendor_name": "Oribtal Foods Group",
        "requested_amount": 880.0,
        "bank_account": "US00-OF-120000",
        "po_number": "PO-12345",
        "reason": "Unknown Vendor",
    },
    {
        "request_id": "REQ-008",
        "vendor_name": "Summit Restaurant Grp",
        "requested_amount": 760.25,
        "bank_account": "US00-SR-000999",
        "po_number": "PO-40404",
        "reason": "Bank Account Mismatch",
    },
    {
        "request_id": "REQ-009",
        "vendor_name": "Northwind Industrial LLC",
        "requested_amount": 18250.0,
        "bank_account": "US00-NW-445566",
        "po_number": None,
        "reason": "Invalid PO",
    },
]

CLEAN_REQUEST_IDS = {"REQ-001", "REQ-007", "REQ-010"}


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_PATH)

    def test_output_schema_and_content(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
            actual = json.load(handle)

        assert isinstance(actual, list), "Output must be a JSON array."

        actual_sorted = sorted(actual, key=lambda item: item["request_id"])
        expected_sorted = sorted(EXPECTED_ANOMALIES, key=lambda item: item["request_id"])

        assert len(actual_sorted) == len(expected_sorted), (
            f"Expected {len(expected_sorted)} anomalies, got {len(actual_sorted)}."
        )

        for item in actual_sorted:
            assert set(item.keys()) == {
                "request_id",
                "vendor_name",
                "requested_amount",
                "bank_account",
                "po_number",
                "reason",
            }, f"Unexpected keys for request {item.get('request_id')}: {sorted(item.keys())}"

        assert actual_sorted == expected_sorted

    def test_clean_requests_are_not_flagged(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
            actual = json.load(handle)

        flagged_ids = {item["request_id"] for item in actual}
        assert not (flagged_ids & CLEAN_REQUEST_IDS), (
            f"Clean requests were incorrectly flagged: {sorted(flagged_ids & CLEAN_REQUEST_IDS)}"
        )
