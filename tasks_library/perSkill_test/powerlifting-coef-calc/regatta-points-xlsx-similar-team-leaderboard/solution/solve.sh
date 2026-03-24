#!/bin/bash

set -euo pipefail

OUTPUT_FILE="/root/data/regatta_team_leaderboard.xlsx"

python3 <<'PY'
from openpyxl import load_workbook

output_file = "/root/data/regatta_team_leaderboard.xlsx"
wb = load_workbook(output_file)
results_ws = wb["Results"]
leaderboard_ws = wb["Leaderboard"]
rules_ws = wb["ScoringRules"]

headers = [
    "Athlete",
    "Team",
    "Event",
    "EventType",
    "Place",
    "Points",
    "TeamTotal",
    "TeamOrder",
]

for col_idx, header in enumerate(headers, start=1):
    leaderboard_ws.cell(row=1, column=col_idx, value=header)

result_last_row = results_ws.max_row
rules_last_row = rules_ws.max_row

for row_idx in range(2, result_last_row + 1):
    leaderboard_ws[f"A{row_idx}"] = f"=Results!A{row_idx}"
    leaderboard_ws[f"B{row_idx}"] = f"=Results!B{row_idx}"
    leaderboard_ws[f"C{row_idx}"] = f"=Results!C{row_idx}"
    leaderboard_ws[f"D{row_idx}"] = f"=Results!D{row_idx}"
    leaderboard_ws[f"E{row_idx}"] = f"=Results!E{row_idx}"
    leaderboard_ws[f"F{row_idx}"] = (
        f'=SUMIFS(ScoringRules!$C$2:$C${rules_last_row},'
        f'ScoringRules!$A$2:$A${rules_last_row},D{row_idx},'
        f'ScoringRules!$B$2:$B${rules_last_row},E{row_idx})'
    )
    leaderboard_ws[f"G{row_idx}"] = (
        f'=SUMIF($B$2:$B${result_last_row},B{row_idx},$F$2:$F${result_last_row})'
    )
    leaderboard_ws[f"H{row_idx}"] = (
        f'=1+SUMPRODUCT(($B$2:$B${result_last_row}=B{row_idx})*($F$2:$F${result_last_row}>F{row_idx}))'
        f'+SUMPRODUCT(($B$2:$B${result_last_row}=B{row_idx})*($F$2:$F${result_last_row}=F{row_idx})*($E$2:$E${result_last_row}<E{row_idx}))'
        f'+SUMPRODUCT(($B$2:$B${result_last_row}=B{row_idx})*($F$2:$F${result_last_row}=F{row_idx})*($E$2:$E${result_last_row}=E{row_idx})*(ROW($A$2:$A${result_last_row})<ROW(A{row_idx})))'
    )

for column, width in {
    "A": 18,
    "B": 14,
    "C": 24,
    "D": 12,
    "E": 10,
    "F": 10,
    "G": 12,
    "H": 11,
}.items():
    leaderboard_ws.column_dimensions[column].width = width

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
