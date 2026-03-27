import os

OUTPUT_FILE = "/root/transfer3_weekday_report.tsv"
EXPECTED_LINES = [
    "weekday\treceipt_count\ttotal_amount\taverage_amount",
    "Monday\t3\t108.24\t36.08",
    "Tuesday\t3\t130.70\t43.57",
    "Wednesday\t3\t207.97\t69.32",
    "Thursday\t5\t682.80\t136.56",
    "Friday\t6\t573.05\t95.51",
    "Saturday\t0\t0.00\t0.00",
    "Sunday\t2\t109.25\t54.63",
    "TOTAL\t22\t1812.01\t82.36",
]

assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    lines = [line.rstrip("\n") for line in f]

assert lines == EXPECTED_LINES, f"TSV mismatch.\nActual: {lines}\nExpected: {EXPECTED_LINES}"
print("transfer3 test passed")
