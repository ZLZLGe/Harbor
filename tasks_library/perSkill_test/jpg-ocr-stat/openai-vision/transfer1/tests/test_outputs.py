import json
import os

OUTPUT_FILE = "/root/transfer1_monthly_totals.json"
EXPECTED = [
    {"month": "2017-02", "receipt_count": 1, "total_amount": "92.80"},
    {"month": "2017-09", "receipt_count": 1, "total_amount": "10.40"},
    {"month": "2017-10", "receipt_count": 1, "total_amount": "23.25"},
    {"month": "2018-02", "receipt_count": 4, "total_amount": "201.31"},
    {"month": "2018-03", "receipt_count": 1, "total_amount": "102.00"},
]

assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

assert data == EXPECTED, f"JSON mismatch.\nActual: {data}\nExpected: {EXPECTED}"
print("transfer1 test passed")
