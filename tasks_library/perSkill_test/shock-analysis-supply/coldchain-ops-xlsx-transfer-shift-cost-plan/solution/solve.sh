#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from openpyxl import load_workbook

template = "coldchain-ops-template.xlsx"
output = "coldchain-ops-plan.xlsx"

wb = load_workbook(template)


def load_csv(ws_name, filename):
    ws = wb[ws_name]
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            ws.append([int(v) if v.isdigit() else float(v) if v.replace(".", "", 1).isdigit() else v for v in row])


load_csv("Store_Demand", "store_daily_demand.csv")
load_csv("Shift_Definitions", "warehouse_shifts.csv")
load_csv("Power_Curve", "equipment_power_curve.csv")
load_csv("Tariff_Template", "tou_tariff_template.csv")

hourly = wb["Hourly_Load"]
for row in range(2, 170):
    hourly[f"C{row}"] = f'=SUMIFS(Store_Demand!$C$2:$C$29,Store_Demand!$A$2:$A$29,$A{row})'
    hourly[f"D{row}"] = f'=INDEX(Planner!$B$9:$B$32,MATCH($B{row},Planner!$A$9:$A$32,0))'
    hourly[f"E{row}"] = f'=$C{row}*$D{row}'
    hourly[f"F{row}"] = f'=INDEX(Power_Curve!$B$2:$B$25,MATCH($B{row},Power_Curve!$A$2:$A$25,0))'
    hourly[f"G{row}"] = f'=INDEX(Power_Curve!$C$2:$C$25,MATCH($B{row},Power_Curve!$A$2:$A$25,0))'
    hourly[f"H{row}"] = f'=INDEX(Power_Curve!$D$2:$D$25,MATCH($B{row},Power_Curve!$A$2:$A$25,0))'
    hourly[f"I{row}"] = f'=INDEX(Power_Curve!$E$2:$E$25,MATCH($B{row},Power_Curve!$A$2:$A$25,0))'
    hourly[f"J{row}"] = f'=$F{row}+$G{row}+$I{row}+$E{row}*$H{row}'
    hourly[f"K{row}"] = f'=INDEX(Tariff_Template!$B$2:$B$25,MATCH($B{row},Tariff_Template!$A$2:$A$25,0))'
    hourly[f"L{row}"] = f'=INDEX(Tariff_Template!$C$2:$C$25,MATCH($B{row},Tariff_Template!$A$2:$A$25,0))'
    hourly[f"M{row}"] = f'=$J{row}*$L{row}'

labor = wb["Labor_Schedule"]
for row in range(2, 23):
    labor[f"C{row}"] = f'=INDEX(Shift_Definitions!$B$2:$B$4,MATCH($B{row},Shift_Definitions!$A$2:$A$4,0))'
    labor[f"D{row}"] = f'=INDEX(Shift_Definitions!$C$2:$C$4,MATCH($B{row},Shift_Definitions!$A$2:$A$4,0))'
    labor[f"E{row}"] = f'=$D{row}-$C{row}'
    labor[f"F{row}"] = f'=INDEX(Shift_Definitions!$E$2:$E$4,MATCH($B{row},Shift_Definitions!$A$2:$A$4,0))'
    labor[f"G{row}"] = (
        f'=SUMIFS(Hourly_Load!$E$2:$E$169,Hourly_Load!$A$2:$A$169,$A{row},'
        f'Hourly_Load!$B$2:$B$169,">="&$C{row},Hourly_Load!$B$2:$B$169,"<"&$D{row})'
    )
    labor[f"H{row}"] = f'=ROUNDUP($G{row}/$E{row}/Planner!$B$2,0)'
    labor[f"I{row}"] = f'=MAX($F{row},$H{row}+Planner!$B$5)'
    labor[f"J{row}"] = f'=$I{row}*$E{row}'
    labor[f"K{row}"] = (
        f'=$I{row}*MAX($E{row}-INDEX(Shift_Definitions!$D$2:$D$4,'
        f'MATCH($B{row},Shift_Definitions!$A$2:$A$4,0)),0)'
    )
    labor[f"L{row}"] = f'=INDEX(Shift_Definitions!$F$2:$F$4,MATCH($B{row},Shift_Definitions!$A$2:$A$4,0))'
    labor[f"M{row}"] = f'=$J{row}*$L{row}'
    labor[f"N{row}"] = (
        f'=$K{row}*$L{row}*(INDEX(Shift_Definitions!$G$2:$G$4,'
        f'MATCH($B{row},Shift_Definitions!$A$2:$A$4,0))-1)'
    )
    labor[f"O{row}"] = f'=$M{row}+$N{row}'

summary = wb["Cost_Summary"]
summary["B2"] = "=SUM(Hourly_Load!$E$2:$E$169)"
summary["B3"] = "=SUM(Hourly_Load!$J$2:$J$169)"
summary["B4"] = '=SUMIFS(Hourly_Load!$M$2:$M$169,Hourly_Load!$K$2:$K$169,"OffPeak")'
summary["B5"] = '=SUMIFS(Hourly_Load!$M$2:$M$169,Hourly_Load!$K$2:$K$169,"Shoulder")'
summary["B6"] = '=SUMIFS(Hourly_Load!$M$2:$M$169,Hourly_Load!$K$2:$K$169,"Peak")'
summary["B7"] = '=SUMIFS(Hourly_Load!$M$2:$M$169,Hourly_Load!$K$2:$K$169,"Critical")'
summary["B8"] = "=SUM(Labor_Schedule!$M$2:$M$22)"
summary["B9"] = "=SUM(Labor_Schedule!$N$2:$N$22)"
summary["B10"] = "=SUM(Labor_Schedule!$O$2:$O$22)"
summary["B11"] = "=SUM(Hourly_Load!$M$2:$M$169)"
summary["B12"] = "=B10+B11"

bridge = wb["Profit_Bridge"]
bridge["B2"] = "=Cost_Summary!$B$2*Planner!$B$3"
bridge["B3"] = "=-Cost_Summary!$B$8"
bridge["B4"] = "=-Cost_Summary!$B$9"
bridge["B5"] = "=-Cost_Summary!$B$11"
bridge["B6"] = "=-Planner!$B$4"
bridge["B7"] = "=SUM(B2:B6)"

for sheet in wb.worksheets:
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.number_format = "0.00"

wb.save(output)
PY

python3 /root/.codex/skills/xlsx/recalc.py coldchain-ops-plan.xlsx 90 >/tmp/coldchain-ops-recalc.json

python3 - <<'PY'
import json

with open("/tmp/coldchain-ops-recalc.json", encoding="utf-8") as f:
    result = json.load(f)

if result.get("status") == "errors_found" or result.get("total_errors"):
    raise SystemExit(f"formula recalc failed: {result}")
PY
