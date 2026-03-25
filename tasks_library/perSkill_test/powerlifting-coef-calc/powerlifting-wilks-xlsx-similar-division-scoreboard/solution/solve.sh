#!/bin/bash

set -euo pipefail

INPUT_FILE="/root/data/regional_meet_template"
OUTPUT_FILE="/root/data/wilks_division_scoreboard.xlsx"

cp "$INPUT_FILE" "$OUTPUT_FILE"

python3 - <<'PY'
from openpyxl import load_workbook

output_file = "/root/data/wilks_division_scoreboard.xlsx"
wb = load_workbook(output_file)
results_ws = wb["MeetResults"]
score_ws = wb["Scoreboard"]

headers = [
    "Name",
    "Division",
    "Sex",
    "BodyweightKg",
    "Best3SquatKg",
    "Best3BenchKg",
    "Best3DeadliftKg",
    "TotalKg",
    "Wilks",
    "DivisionRank",
]

for idx, header in enumerate(headers, start=1):
    score_ws.cell(row=1, column=idx, value=header)

last_row = results_ws.max_row
for row_idx in range(2, last_row + 1):
    score_ws[f"A{row_idx}"] = f"=MeetResults!A{row_idx}"
    score_ws[f"B{row_idx}"] = f"=MeetResults!B{row_idx}"
    score_ws[f"C{row_idx}"] = f"=MeetResults!C{row_idx}"
    score_ws[f"D{row_idx}"] = f"=MeetResults!D{row_idx}"
    score_ws[f"E{row_idx}"] = f"=MeetResults!E{row_idx}"
    score_ws[f"F{row_idx}"] = f"=MeetResults!F{row_idx}"
    score_ws[f"G{row_idx}"] = f"=MeetResults!G{row_idx}"
    score_ws[f"H{row_idx}"] = f"=SUM(E{row_idx}:G{row_idx})"

    bw = f"D{row_idx}"
    total = f"H{row_idx}"
    male_denominator = (
        f"(-216.0475144+16.2606339*{bw}-0.002388645*{bw}^2"
        f"-0.00113732*{bw}^3+0.00000701863*{bw}^4-0.00000001291*{bw}^5)"
    )
    female_denominator = (
        f"(594.31747775582-27.23842536447*{bw}+0.82112226871*{bw}^2"
        f"-0.00930733913*{bw}^3+0.00004731582*{bw}^4-0.00000009054*{bw}^5)"
    )
    score_ws[f"I{row_idx}"] = (
        f'=ROUND(IF(C{row_idx}="M",{total}*(500/{male_denominator}),'
        f'{total}*(500/{female_denominator})),3)'
    )
    score_ws[f"J{row_idx}"] = (
        f'=COUNTIFS($B$2:$B${last_row},B{row_idx},$I$2:$I${last_row},">"&I{row_idx})+1'
    )

wb.save(output_file)
PY

python3 /root/.codex/skills/xlsx/recalc.py "$OUTPUT_FILE" 60
