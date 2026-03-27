import csv
import os

OUTPUT_FILE = "/root/similar_receipt_rows.csv"
EXPECTED_ROWS = [
    ["filename", "date", "total_amount"],
    ["007.jpg", "2019-01-23", "20.00"],
    ["009.jpg", "2018-01-18", "26.60"],
    ["010.jpg", "2017-12-29", "14.10"],
    ["011.jpg", "2017-06-15", "15.00"],
    ["019.jpg", "2018-03-18", "86.00"],
    ["034.jpg", "2018-03-09", "332.30"],
    ["039.jpg", "2018-03-30", "189.75"],
    ["052.jpg", "2018-03-23", "10.00"],
]

assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"

with open(OUTPUT_FILE, "r", encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))

assert rows == EXPECTED_ROWS, f"CSV mismatch.\nActual: {rows}\nExpected: {EXPECTED_ROWS}"
print("similar test passed")
