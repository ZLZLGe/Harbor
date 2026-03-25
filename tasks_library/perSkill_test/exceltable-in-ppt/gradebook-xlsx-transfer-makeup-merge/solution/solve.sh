#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import subprocess
from pathlib import Path

from openpyxl import load_workbook

INPUT_FILE = Path("/root/gradebook_template.xlsx")
CSV_FILE = Path("/root/makeup_scores.csv")
OUTPUT_FILE = Path("/root/makeup_gradebook.xlsx")
RECALC_SCRIPT = Path("/root/.codex/skills/xlsx/recalc.py")


def parse_score(raw):
    text = raw.strip()
    if "." in text:
        value = float(text)
        return int(value) if value.is_integer() else value
    return int(text)


workbook = load_workbook(INPUT_FILE)
sheet = workbook["成绩册"]

header_map = {}
for column in range(1, sheet.max_column + 1):
    header_map[str(sheet.cell(row=1, column=column).value).strip()] = column

student_rows = {}
for row in range(2, sheet.max_row + 1):
    student_id = str(sheet.cell(row=row, column=header_map["学号"]).value).strip()
    student_rows[student_id] = row

column_updates = {
    "小测2补考": "小测2",
    "小测4补考": "小测4",
}

with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
    for record in csv.DictReader(handle):
        student_id = record["学号"].strip()
        row = student_rows.get(student_id)
        if row is None:
            continue
        for source_name, target_name in column_updates.items():
            raw_value = (record.get(source_name) or "").strip()
            if raw_value == "":
                continue
            sheet.cell(row=row, column=header_map[target_name]).value = parse_score(raw_value)

workbook.save(OUTPUT_FILE)
workbook.close()

result = subprocess.run(
    ["python3", str(RECALC_SCRIPT), str(OUTPUT_FILE), "60"],
    check=True,
    capture_output=True,
    text=True,
)
print(result.stdout)

payload = json.loads(result.stdout)
if payload.get("status") != "success":
    raise SystemExit(f"公式重算异常: {payload}")
PY
