#!/bin/bash

set -euo pipefail

INPUT_FILE="/root/data/course_gradebook_template.xlsx"
OUTPUT_FILE="/root/data/term_grade_report.xlsx"
RECALC_SCRIPT="/root/.codex/skills/xlsx/recalc.py"

cp "$INPUT_FILE" "$OUTPUT_FILE"

python3 - <<'PY'
from openpyxl import load_workbook

output_file = "/root/data/term_grade_report.xlsx"
wb = load_workbook(output_file)
scores_ws = wb["Scores"]
report_ws = wb["Report"]

headers = [
    "StudentID",
    "StudentName",
    "Homework",
    "Midterm",
    "Project",
    "FinalExam",
    "WeightedTotal",
    "MissingFlag",
    "LetterGrade",
    "PassStatus",
]

for idx, header in enumerate(headers, start=1):
    report_ws.cell(row=1, column=idx, value=header)

last_row = scores_ws.max_row

for row_idx in range(2, last_row + 1):
    report_ws[f"A{row_idx}"] = f"=Scores!A{row_idx}"
    report_ws[f"B{row_idx}"] = f"=Scores!B{row_idx}"
    report_ws[f"C{row_idx}"] = f'=IF(Scores!C{row_idx}="","",Scores!C{row_idx})'
    report_ws[f"D{row_idx}"] = f'=IF(Scores!D{row_idx}="","",Scores!D{row_idx})'
    report_ws[f"E{row_idx}"] = f'=IF(Scores!E{row_idx}="","",Scores!E{row_idx})'
    report_ws[f"F{row_idx}"] = f'=IF(Scores!F{row_idx}="","",Scores!F{row_idx})'
    report_ws[f"G{row_idx}"] = f"=ROUND(SUMPRODUCT(C{row_idx}:F{row_idx},Weights!$A$2:$D$2),2)"
    report_ws[f"H{row_idx}"] = f'=IF(COUNTBLANK(C{row_idx}:F{row_idx})>0,"MISSING","OK")'
    report_ws[f"I{row_idx}"] = f"=LOOKUP(G{row_idx},GradeBands!$A$2:$A$6,GradeBands!$B$2:$B$6)"
    report_ws[f"J{row_idx}"] = f"=LOOKUP(G{row_idx},GradeBands!$A$2:$A$6,GradeBands!$C$2:$C$6)"
    report_ws[f"G{row_idx}"].number_format = "0.00"

for col, width in {
    "A": 12,
    "B": 18,
    "C": 12,
    "D": 12,
    "E": 12,
    "F": 12,
    "G": 14,
    "H": 14,
    "I": 12,
    "J": 12,
}.items():
    report_ws.column_dimensions[col].width = width

report_ws.freeze_panes = "A2"
wb.save(output_file)
PY

python3 "$RECALC_SCRIPT" "$OUTPUT_FILE" 60 > /tmp/course_gradebook_recalc.json

python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("/tmp/course_gradebook_recalc.json").read_text())
if result.get("status") != "success":
    raise SystemExit(f"Recalculation failed: {result}")
PY
