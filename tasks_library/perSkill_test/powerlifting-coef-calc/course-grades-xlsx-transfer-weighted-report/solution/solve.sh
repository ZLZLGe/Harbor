#!/bin/bash

set -euo pipefail

OUTPUT_FILE="/root/data/course_weighted_report.xlsx"

python3 <<'PY'
from openpyxl import load_workbook

output_file = "/root/data/course_weighted_report.xlsx"
wb = load_workbook(output_file)
roster_ws = wb["Roster"]
scores_ws = wb["Scores"]
weights_ws = wb["Weights"]
report_ws = wb["Report"]

headers = [
    "StudentID",
    "Section",
    "LastName",
    "FirstName",
    "Quiz1",
    "Quiz2",
    "Quiz3",
    "Quiz4",
    "DroppedQuiz",
    "QuizAverage",
    "Lab1",
    "Lab2",
    "LabAverage",
    "Midterm",
    "FinalExam",
    "QuizWeighted",
    "LabWeighted",
    "MidtermWeighted",
    "FinalWeighted",
    "TotalScore",
    "LetterGrade",
]

for col_idx, header in enumerate(headers, start=1):
    report_ws.cell(row=1, column=col_idx, value=header)

roster_last_row = roster_ws.max_row
scores_last_row = scores_ws.max_row
weights_last_row = weights_ws.max_row

score_ranges = {
    "Quiz1": "B",
    "Quiz2": "C",
    "Quiz3": "D",
    "Quiz4": "E",
    "Lab1": "F",
    "Lab2": "G",
    "Midterm": "H",
    "FinalExam": "I",
}

for row_idx in range(2, roster_last_row + 1):
    report_ws[f"A{row_idx}"] = f"=Roster!A{row_idx}"
    report_ws[f"B{row_idx}"] = f"=Roster!B{row_idx}"
    report_ws[f"C{row_idx}"] = f"=Roster!C{row_idx}"
    report_ws[f"D{row_idx}"] = f"=Roster!D{row_idx}"

    for target_col, score_name in zip(
        ("E", "F", "G", "H", "K", "L", "N", "O"),
        ("Quiz1", "Quiz2", "Quiz3", "Quiz4", "Lab1", "Lab2", "Midterm", "FinalExam"),
    ):
        source_col = score_ranges[score_name]
        report_ws[f"{target_col}{row_idx}"] = (
            f"=INDEX(Scores!${source_col}$2:${source_col}${scores_last_row},"
            f'MATCH($A{row_idx},Scores!$A$2:$A${scores_last_row},0))'
        )

    report_ws[f"I{row_idx}"] = f"=MIN(E{row_idx}:H{row_idx})"
    report_ws[f"J{row_idx}"] = (
        f"=ROUND((SUM(E{row_idx}:H{row_idx})-I{row_idx})/(COUNT(E{row_idx}:H{row_idx})-1),2)"
    )
    report_ws[f"M{row_idx}"] = f"=ROUND(AVERAGE(K{row_idx}:L{row_idx}),2)"
    report_ws[f"P{row_idx}"] = (
        f'=ROUND(J{row_idx}*INDEX(Weights!$B$2:$B${weights_last_row},'
        f'MATCH("Quiz",Weights!$A$2:$A${weights_last_row},0)),2)'
    )
    report_ws[f"Q{row_idx}"] = (
        f'=ROUND(M{row_idx}*INDEX(Weights!$B$2:$B${weights_last_row},'
        f'MATCH("Lab",Weights!$A$2:$A${weights_last_row},0)),2)'
    )
    report_ws[f"R{row_idx}"] = (
        f'=ROUND(N{row_idx}*INDEX(Weights!$B$2:$B${weights_last_row},'
        f'MATCH("Midterm",Weights!$A$2:$A${weights_last_row},0)),2)'
    )
    report_ws[f"S{row_idx}"] = (
        f'=ROUND(O{row_idx}*INDEX(Weights!$B$2:$B${weights_last_row},'
        f'MATCH("FinalExam",Weights!$A$2:$A${weights_last_row},0)),2)'
    )
    report_ws[f"T{row_idx}"] = f"=ROUND(SUM(P{row_idx}:S{row_idx}),2)"
    report_ws[f"U{row_idx}"] = (
        f'=IF(T{row_idx}>=90,"A",IF(T{row_idx}>=80,"B",IF(T{row_idx}>=70,"C",IF(T{row_idx}>=60,"D","F"))))'
    )

for column, width in {
    "A": 12,
    "B": 10,
    "C": 14,
    "D": 14,
    "E": 9,
    "F": 9,
    "G": 9,
    "H": 9,
    "I": 12,
    "J": 12,
    "K": 9,
    "L": 9,
    "M": 11,
    "N": 10,
    "O": 11,
    "P": 13,
    "Q": 12,
    "R": 16,
    "S": 14,
    "T": 11,
    "U": 12,
}.items():
    report_ws.column_dimensions[column].width = width

for column in ("J", "M", "P", "Q", "R", "S", "T"):
    for cell in report_ws[column][1:]:
        cell.number_format = "0.00"

wb.save(output_file)
PY

recalc_json="$(python3 /root/.codex/skills/xlsx/recalc.py "$OUTPUT_FILE" 90)"
printf '%s\n' "$recalc_json"

python3 <<'PY' "$recalc_json"
import json
import sys

result = json.loads(sys.argv[1])
if result.get("status") != "success":
    raise SystemExit(f"Formula recalculation failed: {result}")
PY
