#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
from openpyxl import load_workbook

template = "/root/bottling-expansion-template.xlsx"
output = "/root/bottling-expansion-model.xlsx"

wb = load_workbook(template)

trend = wb["Efficiency_Trend"]
for row in range(2, 9):
    src = row
    trend[f"B{row}"] = f"=Historical_Data!B{src}"
    trend[f"C{row}"] = f"=Historical_Data!C{src}"
    trend[f"D{row}"] = f"=Historical_Data!D{src}"
    trend[f"E{row}"] = f"=B{row}/D{row}"
    trend[f"F{row}"] = f"=B{row}/C{row}"
    trend[f"G{row}"] = f"=SQRT(E{row}*F{row})"

trend["H2"] = "=G2"
trend["H3"] = "=G3"
for row in range(4, 9):
    trend[f"H{row}"] = f"=0.2*G{row-2}+0.3*G{row-1}+0.5*G{row}"
for row in range(9, 14):
    trend[f"H{row}"] = f"=TREND($H$2:$H$8,$A$2:$A$8,A{row})"
for row in range(3, 14):
    trend[f"I{row}"] = f"=H{row}/H{row-1}-1"

model = wb["Capacity_Model"]
for row in range(2, 8):
    model[f"B{row}"] = f"=INDEX(Efficiency_Trend!$H$2:$H$13,MATCH(A{row},Efficiency_Trend!$A$2:$A$13,0))"

model["C2"] = "=0"
for row in range(3, 8):
    model[f"C{row}"] = f"=B{row}/B{row-1}-1"

model["D2"] = "=0"
for row in range(3, 8):
    model[f"D{row}"] = f"=MIN(C{row},Assumptions!$B$6)"

model["E2"] = "=Historical_Data!B8"
for row in range(3, 8):
    model[f"E{row}"] = f"=E{row-1}*(1+D{row})"

model["F2"] = "=0"
model["G2"] = "=0"
for row in range(3, 8):
    model[f"F{row}"] = f"=INDEX(Expansion_Plan!$B$2:$B$6,MATCH(A{row},Expansion_Plan!$A$2:$A$6,0))"
    model[f"G{row}"] = f"=INDEX(Expansion_Plan!$C$2:$C$6,MATCH(A{row},Expansion_Plan!$A$2:$A$6,0))"

model["H2"] = "=0"
for row in range(3, 8):
    model[f"H{row}"] = f"=H{row-1}+G{row}"

model["I2"] = "=E2"
for row in range(3, 8):
    model[f"I{row}"] = f"=E{row}+H{row}*(B{row}/$B$2)*Assumptions!$B$7"

model["J2"] = "=0"
for row in range(3, 8):
    model[f"J{row}"] = f"=J{row-1}-K{row}+F{row}"

model["K2"] = "=0"
for row in range(3, 8):
    model[f"K{row}"] = f"=J{row-1}/Assumptions!$B$5"

model["L2"] = "=0"
for row in range(3, 8):
    model[f"L{row}"] = f"=(I{row}-E{row})*(Assumptions!$B$2-Assumptions!$B$3)-J{row}*Assumptions!$B$4"

model["M2"] = "=0"
for row in range(3, 8):
    model[f"M{row}"] = f"=L{row}-K{row}"

summary = wb["Summary"]
summary["B2"] = "=SUM(Capacity_Model!L3:L7)"
summary["B3"] = "=SUM(Capacity_Model!K3:K7)"
summary["B4"] = "=Capacity_Model!I7"
for offset, model_row in enumerate(range(3, 8), start=7):
    summary[f"E{offset}"] = f"=Capacity_Model!L{model_row}"
    summary[f"H{offset}"] = f"=Capacity_Model!K{model_row}"

wb.save(output)
PY

mkdir -p /tmp/bottling-recalc
cp /root/bottling-expansion-model.xlsx /tmp/bottling-recalc/bottling-expansion-model.xlsx
libreoffice --headless --convert-to ods --outdir /tmp/bottling-recalc /tmp/bottling-recalc/bottling-expansion-model.xlsx >/tmp/bottling-recalc/convert1.log 2>&1
rm -f /root/bottling-expansion-model.xlsx
libreoffice --headless --convert-to xlsx:"Calc MS Excel 2007 XML" --outdir /root /tmp/bottling-recalc/bottling-expansion-model.ods >/tmp/bottling-recalc/convert2.log 2>&1
