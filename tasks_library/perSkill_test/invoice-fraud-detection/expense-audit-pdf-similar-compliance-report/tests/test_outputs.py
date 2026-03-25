import json
from pathlib import Path


OUTPUT_PATH = Path("/root/expense_exceptions.json")
EXPECTED = [
    {
        "expense_page_number": 2,
        "employee_name": "Mila Stone",
        "travel_city": "Seattle",
        "approval_code": "TA-4827",
        "reimbursement_amount": 760.0,
        "payout_account": "AC-7799-08",
        "reason": "Unknown Employee",
    },
    {
        "expense_page_number": 3,
        "employee_name": "Bruno Diaz",
        "travel_city": "Chicago",
        "approval_code": "TA-4822",
        "reimbursement_amount": 855.0,
        "payout_account": "AC-0000-02",
        "reason": "Account Mismatch",
    },
    {
        "expense_page_number": 4,
        "employee_name": "Carla Reed",
        "travel_city": "Boston",
        "approval_code": "TA-9999",
        "reimbursement_amount": 630.0,
        "payout_account": "AC-7788-03",
        "reason": "Invalid Approval",
    },
    {
        "expense_page_number": 5,
        "employee_name": "Elena Park",
        "travel_city": "Denver",
        "approval_code": "TA-4824",
        "reimbursement_amount": 715.0,
        "payout_account": "AC-7788-05",
        "reason": "Employee Mismatch",
    },
    {
        "expense_page_number": 6,
        "employee_name": "Deepak Nair",
        "travel_city": "Denver",
        "approval_code": "TA-4824",
        "reimbursement_amount": 920.0,
        "payout_account": "AC-7788-04",
        "reason": "City Mismatch",
    },
    {
        "expense_page_number": 7,
        "employee_name": "Felix Moore",
        "travel_city": "Atlanta",
        "approval_code": "TA-4826",
        "reimbursement_amount": 572.4,
        "payout_account": "AC-7788-06",
        "reason": "Over Policy Limit",
    },
    {
        "expense_page_number": 9,
        "employee_name": "Alice Wong",
        "travel_city": "Seattle",
        "approval_code": None,
        "reimbursement_amount": 410.0,
        "payout_account": "AC-7788-01",
        "reason": "Invalid Approval",
    },
]

REQUIRED_KEYS = {
    "expense_page_number",
    "employee_name",
    "travel_city",
    "approval_code",
    "reimbursement_amount",
    "payout_account",
    "reason",
}

ALLOWED_REASONS = {
    "Unknown Employee",
    "Account Mismatch",
    "Invalid Approval",
    "Employee Mismatch",
    "City Mismatch",
    "Over Policy Limit",
}


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/expense_exceptions.json"


def test_output_schema_and_order():
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)

    page_numbers = []
    for item in data:
        assert set(item.keys()) == REQUIRED_KEYS
        assert isinstance(item["expense_page_number"], int)
        assert isinstance(item["employee_name"], str)
        assert isinstance(item["travel_city"], str)
        assert item["approval_code"] is None or isinstance(item["approval_code"], str)
        assert isinstance(item["reimbursement_amount"], (int, float))
        assert isinstance(item["payout_account"], str)
        assert item["reason"] in ALLOWED_REASONS
        page_numbers.append(item["expense_page_number"])

    assert page_numbers == sorted(page_numbers), "results must be sorted by expense_page_number ascending"


def test_expected_exceptions_only():
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert data == EXPECTED
