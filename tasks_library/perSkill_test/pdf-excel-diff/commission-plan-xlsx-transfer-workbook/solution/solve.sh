#!/bin/bash
set -euo pipefail

cat > /tmp/build_commission_payouts.py <<'PY'
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

SALES_FILE = Path("/root/sales_detail_2026Q1.xlsx")
QUOTA_FILE = Path("/root/team_quota_plan_2026.xlsx")
OUTPUT_FILE = Path("/root/commission_payouts.xlsx")
RECALC_SCRIPT = Path("/root/.codex/skills/xlsx/recalc.py")


def rows_from_sheet(path: Path, sheet_name: str) -> list[dict[str, object]]:
    workbook = load_workbook(path, data_only=False)
    sheet = workbook[sheet_name]
    rows = list(sheet.iter_rows(values_only=True))
    headers = [str(value) for value in rows[0]]
    payload = [dict(zip(headers, row)) for row in rows[1:]]
    workbook.close()
    return payload


def style_header(sheet) -> None:
    fill = PatternFill("solid", fgColor="1F4E78")
    font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = font


quota_rows = rows_from_sheet(QUOTA_FILE, "Rep Targets")
sales_rows = rows_from_sheet(SALES_FILE, "Closed Deals")
sales_rows.sort(key=lambda row: str(row["sale_id"]))

workbook = Workbook()
quota_sheet = workbook.active
quota_sheet.title = "Quota Plan"
detail_sheet = workbook.create_sheet("Commission Detail")
summary_sheet = workbook.create_sheet("Team Overview")

quota_headers = [
    "rep_id",
    "rep_name",
    "team",
    "monthly_quota",
    "standard_rate",
    "stretch_rate",
]
quota_sheet.append(quota_headers)
for row in quota_rows:
    quota_sheet.append([row[header] for header in quota_headers])

detail_headers = [
    "sale_id",
    "sale_month",
    "rep_id",
    "rep_name",
    "team",
    "client",
    "net_revenue",
    "monthly_quota",
    "monthly_revenue",
    "attainment",
    "applied_rate",
    "commission",
]
detail_sheet.append(detail_headers)

quota_last_row = len(quota_rows) + 1
detail_last_row = len(sales_rows) + 1
quota_range = f"'Quota Plan'!$A$2:$F${quota_last_row}"

for index, row in enumerate(sales_rows, start=2):
    detail_sheet.cell(index, 1, row["sale_id"])
    detail_sheet.cell(index, 2, row["sale_month"])
    detail_sheet.cell(index, 3, row["rep_id"])
    detail_sheet.cell(index, 4, f"=VLOOKUP(C{index},{quota_range},2,FALSE)")
    detail_sheet.cell(index, 5, f"=VLOOKUP(C{index},{quota_range},3,FALSE)")
    detail_sheet.cell(index, 6, row["client"])
    detail_sheet.cell(index, 7, row["net_revenue"])
    detail_sheet.cell(index, 8, f"=VLOOKUP(C{index},{quota_range},4,FALSE)")
    detail_sheet.cell(index, 9, f'=SUMIFS($G$2:$G${detail_last_row},$C$2:$C${detail_last_row},$C{index},$B$2:$B${detail_last_row},$B{index})')
    detail_sheet.cell(index, 10, f"=I{index}/H{index}")
    detail_sheet.cell(index, 11, f"=IF(J{index}>=1.1,VLOOKUP(C{index},{quota_range},6,FALSE),VLOOKUP(C{index},{quota_range},5,FALSE))")
    detail_sheet.cell(index, 12, f"=ROUND(G{index}*K{index},2)")

team_names = sorted({str(row['team']) for row in quota_rows})
summary_headers = ["team", "quota_total", "total_revenue", "total_commission", "attainment"]
summary_sheet.append(summary_headers)
for index, team in enumerate(team_names, start=2):
    summary_sheet.cell(index, 1, team)
    summary_sheet.cell(index, 2, f"=SUMIF('Quota Plan'!$C$2:$C${quota_last_row},A{index},'Quota Plan'!$D$2:$D${quota_last_row})")
    summary_sheet.cell(index, 3, f"=SUMIF('Commission Detail'!$E$2:$E${detail_last_row},A{index},'Commission Detail'!$G$2:$G${detail_last_row})")
    summary_sheet.cell(index, 4, f"=SUMIF('Commission Detail'!$E$2:$E${detail_last_row},A{index},'Commission Detail'!$L$2:$L${detail_last_row})")
    summary_sheet.cell(index, 5, f"=C{index}/B{index}")

for sheet in (quota_sheet, detail_sheet, summary_sheet):
    style_header(sheet)
    sheet.freeze_panes = "A2"

for row in quota_sheet.iter_rows(min_row=2, min_col=4, max_col=6):
    for cell in row:
        cell.number_format = "0.0%"
        if cell.column == 4:
            cell.number_format = "$#,##0.00"

for row in detail_sheet.iter_rows(min_row=2, min_col=7, max_col=12):
    for cell in row:
        if cell.column in {10, 11}:
            cell.number_format = "0.0%"
        else:
            cell.number_format = "$#,##0.00"

for row in summary_sheet.iter_rows(min_row=2, min_col=2, max_col=5):
    for cell in row:
        if cell.column == 5:
            cell.number_format = "0.0%"
        else:
            cell.number_format = "$#,##0.00"

column_widths = {
    "Quota Plan": {"A": 12, "B": 18, "C": 12, "D": 15, "E": 14, "F": 14},
    "Commission Detail": {"A": 12, "B": 12, "C": 12, "D": 18, "E": 12, "F": 20, "G": 14, "H": 14, "I": 14, "J": 12, "K": 12, "L": 14},
    "Team Overview": {"A": 12, "B": 14, "C": 14, "D": 16, "E": 12},
}

for sheet_name, widths in column_widths.items():
    sheet = workbook[sheet_name]
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width

workbook.save(OUTPUT_FILE)

result = subprocess.run(
    ["python3", str(RECALC_SCRIPT), str(OUTPUT_FILE), "60"],
    check=True,
    capture_output=True,
    text=True,
)
payload = json.loads(result.stdout)
if payload.get("status") != "success":
    raise SystemExit(f"Recalculation failed: {payload}")
PY

python3 /tmp/build_commission_payouts.py
