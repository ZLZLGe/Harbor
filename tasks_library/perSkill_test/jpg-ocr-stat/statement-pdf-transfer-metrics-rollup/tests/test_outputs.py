import json
import os


OUTPUT_FILE = "/app/workspace/statement_metrics.json"

EXPECTED = {
    "source_dir": "/app/workspace/monthly_statements",
    "statement_count": 4,
    "account_id": "ACCT-77821",
    "statements": [
        {
            "filename": "ops_statement_2024_01.pdf",
            "statement_id": "TFS-2401-118",
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "total_due": "57.50",
            "fee_count": 4,
            "largest_fee": {"fee_code": "LATE_FEE", "amount": "34.00"},
        },
        {
            "filename": "ops_statement_2024_02.pdf",
            "statement_id": "TFS-2402-118",
            "period_start": "2024-02-01",
            "period_end": "2024-02-29",
            "total_due": "41.25",
            "fee_count": 5,
            "largest_fee": {"fee_code": "WIRE_FEE", "amount": "18.00"},
        },
        {
            "filename": "ops_statement_2024_03.pdf",
            "statement_id": "TFS-2403-118",
            "period_start": "2024-03-01",
            "period_end": "2024-03-31",
            "total_due": "86.25",
            "fee_count": 6,
            "largest_fee": {"fee_code": "LATE_FEE", "amount": "20.00"},
        },
        {
            "filename": "ops_statement_2024_04.pdf",
            "statement_id": "TFS-2404-118",
            "period_start": "2024-04-01",
            "period_end": "2024-04-30",
            "total_due": "63.00",
            "fee_count": 7,
            "largest_fee": {"fee_code": "WIRE_FEE", "amount": "18.00"},
        },
    ],
    "rollups": {
        "grand_total_due": "248.00",
        "average_statement_total_due": "62.00",
        "fee_counts_by_code": {
            "ATM_FEE": 3,
            "FOREIGN_SERVICE_FEE": 2,
            "LATE_FEE": 3,
            "MAINTENANCE_FEE": 3,
            "PAPER_STMT_FEE": 4,
            "RESEARCH_FEE": 1,
            "RUSH_REPORT_FEE": 1,
            "WIRE_FEE": 5,
        },
        "fee_totals_by_code": {
            "ATM_FEE": "9.50",
            "FOREIGN_SERVICE_FEE": "30.50",
            "LATE_FEE": "59.00",
            "MAINTENANCE_FEE": "36.00",
            "PAPER_STMT_FEE": "9.00",
            "RESEARCH_FEE": "5.75",
            "RUSH_REPORT_FEE": "8.25",
            "WIRE_FEE": "90.00",
        },
        "monthly_totals": [
            {"month": "2024-01", "total_due": "57.50", "fee_count": 4},
            {"month": "2024-02", "total_due": "41.25", "fee_count": 5},
            {"month": "2024-03", "total_due": "86.25", "fee_count": 6},
            {"month": "2024-04", "total_due": "63.00", "fee_count": 7},
        ],
        "highest_total_due_statement": {
            "filename": "ops_statement_2024_03.pdf",
            "statement_id": "TFS-2403-118",
            "total_due": "86.25",
        },
        "statements_with_late_fee": [
            "ops_statement_2024_01.pdf",
            "ops_statement_2024_03.pdf",
            "ops_statement_2024_04.pdf",
        ],
    },
}


def load_output():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_output_exists():
    assert os.path.exists(OUTPUT_FILE), "statement_metrics.json not found at /app/workspace"


def test_json_structure_and_exact_values():
    payload = load_output()

    assert list(payload.keys()) == ["source_dir", "statement_count", "account_id", "statements", "rollups"], (
        "Top-level keys mismatch.\n"
        f"Actual keys: {list(payload.keys())}"
    )

    assert payload["statements"] == sorted(payload["statements"], key=lambda item: item["filename"]), (
        "statements must be sorted by filename."
    )

    months = [item["month"] for item in payload["rollups"]["monthly_totals"]]
    assert months == sorted(months), "monthly_totals must be sorted by month."

    for statement in payload["statements"]:
        assert set(statement.keys()) == {
            "filename",
            "statement_id",
            "period_start",
            "period_end",
            "total_due",
            "fee_count",
            "largest_fee",
        }, f"Unexpected statement keys: {statement.keys()}"
        assert set(statement["largest_fee"].keys()) == {"fee_code", "amount"}

    assert payload == EXPECTED, (
        "statement_metrics.json content mismatch.\n"
        f"Actual: {json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        f"Expected: {json.dumps(EXPECTED, ensure_ascii=False, indent=2)}"
    )
