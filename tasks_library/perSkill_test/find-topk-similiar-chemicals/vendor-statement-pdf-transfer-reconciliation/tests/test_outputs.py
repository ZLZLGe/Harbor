import csv
from decimal import Decimal
from pathlib import Path


OUTPUT_PATH = Path("/root/workspace/reconciliation.csv")

EXPECTED_ROWS = [
    {
        "vendor_id": "V-104",
        "vendor_name": "Atlas Industrial Supply",
        "amount_due": Decimal("2775.50"),
        "amount_paid": Decimal("2460.50"),
        "difference": Decimal("315.00"),
    },
    {
        "vendor_id": "V-208",
        "vendor_name": "Beacon Clinical Devices",
        "amount_due": Decimal("2735.00"),
        "amount_paid": Decimal("1550.00"),
        "difference": Decimal("1185.00"),
    },
    {
        "vendor_id": "V-315",
        "vendor_name": "Cedar Packaging Co",
        "amount_due": Decimal("1154.50"),
        "amount_paid": Decimal("1100.00"),
        "difference": Decimal("54.50"),
    },
    {
        "vendor_id": "V-412",
        "vendor_name": "Delta Process Controls",
        "amount_due": Decimal("2685.40"),
        "amount_paid": Decimal("2475.40"),
        "difference": Decimal("210.00"),
    },
]

EXPECTED_COLUMNS = ["vendor_id", "vendor_name", "amount_due", "amount_paid", "difference"]


def read_rows():
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return reader.fieldnames, rows


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/workspace/reconciliation.csv"


def test_schema_and_row_order():
    fieldnames, rows = read_rows()
    assert fieldnames == EXPECTED_COLUMNS, "CSV 列名或列顺序不正确"
    assert [row["vendor_id"] for row in rows] == [item["vendor_id"] for item in EXPECTED_ROWS], "数据行顺序必须按 vendor_id 升序"


def test_values_match_expected_totals():
    _, rows = read_rows()
    assert len(rows) == len(EXPECTED_ROWS), "供应商行数不正确"

    for row, expected in zip(rows, EXPECTED_ROWS):
        assert row["vendor_id"] == expected["vendor_id"]
        assert row["vendor_name"] == expected["vendor_name"]

        for amount_key in ["amount_due", "amount_paid", "difference"]:
            assert Decimal(row[amount_key]) == expected[amount_key], f"{expected['vendor_id']} 的 {amount_key} 不正确"
            assert row[amount_key] == f"{expected[amount_key]:.2f}", f"{expected['vendor_id']} 的 {amount_key} 必须保留两位小数"
