import csv
from pathlib import Path


OUTPUT_PATH = Path("/app/output/shelf_audit.csv")
EXPECTED_HEADER = ["photo_id", "product_name", "target_facings", "visible_facings", "audit_status"]
EXPECTED_ROWS = [
    {
        "photo_id": "cooler_left",
        "product_name": "Citrus Pop",
        "target_facings": "3",
        "visible_facings": "3",
        "audit_status": "ok",
    },
    {
        "photo_id": "cooler_left",
        "product_name": "Berry Fizz",
        "target_facings": "2",
        "visible_facings": "1",
        "audit_status": "understocked",
    },
    {
        "photo_id": "cooler_left",
        "product_name": "Spring Water",
        "target_facings": "2",
        "visible_facings": "0",
        "audit_status": "out_of_stock",
    },
    {
        "photo_id": "checkout_endcap",
        "product_name": "Choco Bar",
        "target_facings": "4",
        "visible_facings": "2",
        "audit_status": "understocked",
    },
    {
        "photo_id": "checkout_endcap",
        "product_name": "Salt Chips",
        "target_facings": "3",
        "visible_facings": "3",
        "audit_status": "ok",
    },
    {
        "photo_id": "checkout_endcap",
        "product_name": "Gum Mint",
        "target_facings": "2",
        "visible_facings": "1",
        "audit_status": "understocked",
    },
    {
        "photo_id": "night_fridge",
        "product_name": "Yogurt Drink",
        "target_facings": "2",
        "visible_facings": "2",
        "audit_status": "ok",
    },
    {
        "photo_id": "night_fridge",
        "product_name": "Cold Brew",
        "target_facings": "2",
        "visible_facings": "0",
        "audit_status": "out_of_stock",
    },
    {
        "photo_id": "night_fridge",
        "product_name": "Orange Juice",
        "target_facings": "3",
        "visible_facings": "4",
        "audit_status": "ok",
    },
]


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /app/output/shelf_audit.csv"


def test_csv_contract_and_values():
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows, "CSV 不能为空"
    assert rows[0] == EXPECTED_HEADER, f"CSV 表头错误，期望 {EXPECTED_HEADER}，实际 {rows[0]}"

    actual_rows = []
    for index, row in enumerate(rows[1:], start=2):
        assert len(row) == len(EXPECTED_HEADER), f"第 {index} 行列数错误：{row}"
        actual_rows.append(dict(zip(EXPECTED_HEADER, row)))

    assert actual_rows == EXPECTED_ROWS, f"CSV 内容错误。\n实际: {actual_rows}\n期望: {EXPECTED_ROWS}"

    for row in actual_rows:
        assert row["audit_status"] in {"ok", "understocked", "out_of_stock"}
        int(row["target_facings"])
        int(row["visible_facings"])
