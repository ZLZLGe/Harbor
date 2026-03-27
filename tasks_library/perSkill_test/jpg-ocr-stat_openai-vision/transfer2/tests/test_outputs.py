import csv
import os

OUTPUT_FILE = "/root/transfer2_amount_bands.csv"
EXPECTED = [
    ["band", "receipt_count", "total_amount", "share_percent"],
    ["low_lt_20", "3", "29.70", "4.31"],
    ["mid_20_to_99_99", "2", "120.80", "17.55"],
    ["high_ge_100", "1", "538.00", "78.14"],
]

assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
with open(OUTPUT_FILE, "r", encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))

assert rows == EXPECTED, f"CSV mismatch.\nActual: {rows}\nExpected: {EXPECTED}"
print("transfer2 test passed")
