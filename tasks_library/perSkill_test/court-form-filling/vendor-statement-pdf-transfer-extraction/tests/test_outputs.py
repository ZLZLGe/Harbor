import json
import re
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/invoice-summary.json")

EXPECTED_INVOICES = [
    {
        "invoice_number": "BR-4817",
        "statement_date": "2026-02-28",
        "due_date": "2026-03-02",
        "amount_due": "1245.50",
    },
    {
        "invoice_number": "BR-4824",
        "statement_date": "2026-02-28",
        "due_date": "2026-03-07",
        "amount_due": "875.00",
    },
    {
        "invoice_number": "BR-4839",
        "statement_date": "2026-02-28",
        "due_date": "2026-03-13",
        "amount_due": "2100.00",
    },
    {
        "invoice_number": "BR-4844",
        "statement_date": "2026-02-28",
        "due_date": "2026-03-21",
        "amount_due": "640.75",
    },
    {
        "invoice_number": "BR-4851",
        "statement_date": "2026-02-28",
        "due_date": "2026-03-26",
        "amount_due": "315.20",
    },
]


@pytest.fixture(scope="module")
def output_data():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Output file not found at {OUTPUT_FILE}")

    try:
        return json.loads(OUTPUT_FILE.read_text())
    except json.JSONDecodeError as exc:
        pytest.fail(f"Output is not valid JSON: {exc}")


def test_top_level_shape(output_data):
    assert isinstance(output_data, dict), "Top-level JSON must be an object."
    assert set(output_data.keys()) == {"invoices"}, "Top-level JSON must contain only the 'invoices' key."
    assert isinstance(output_data["invoices"], list), "'invoices' must be a list."


def test_invoice_rows_exact(output_data):
    assert output_data["invoices"] == EXPECTED_INVOICES


@pytest.mark.parametrize("invoice", EXPECTED_INVOICES, ids=[item["invoice_number"] for item in EXPECTED_INVOICES])
def test_invoice_field_formats(output_data, invoice):
    row = next(item for item in output_data["invoices"] if item["invoice_number"] == invoice["invoice_number"])
    assert re.fullmatch(r"BR-\d{4}", row["invoice_number"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["statement_date"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["due_date"])
    assert re.fullmatch(r"\d+\.\d{2}", row["amount_due"])
    assert "$" not in row["amount_due"]
    assert "," not in row["amount_due"]
