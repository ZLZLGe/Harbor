#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
from openpyxl import load_workbook

path = "/root/energy_budget_audit.xlsx"
wb = load_workbook(path)
ws = wb["BudgetAudit"]

for row in range(7, 13):
    ws[f"C{row}"] = f'=VLOOKUP($A{row},BuildingInfo!$A:$D,3,FALSE)'
    ws[f"D{row}"] = f'=VLOOKUP($A{row},BuildingInfo!$A:$D,4,FALSE)'
    ws[f"E{row}"] = f'=SUMIFS(MeterReadings!$E:$E,MeterReadings!$B:$B,$A{row},MeterReadings!$C:$C,$B$2,MeterReadings!$D:$D,E$5)'
    ws[f"F{row}"] = f'=SUMIFS(MeterReadings!$E:$E,MeterReadings!$B:$B,$A{row},MeterReadings!$C:$C,$B$2,MeterReadings!$D:$D,F$5)'
    ws[f"G{row}"] = f'=SUMIFS(MeterReadings!$E:$E,MeterReadings!$B:$B,$A{row},MeterReadings!$C:$C,$B$2,MeterReadings!$D:$D,G$5)'
    ws[f"H{row}"] = f'=SUMIFS(TariffTable!$C:$C,TariffTable!$A:$A,$B$2,TariffTable!$B:$B,H$5)'
    ws[f"I{row}"] = f'=SUMIFS(TariffTable!$C:$C,TariffTable!$A:$A,$B$2,TariffTable!$B:$B,I$5)'
    ws[f"J{row}"] = f'=SUMIFS(TariffTable!$C:$C,TariffTable!$A:$A,$B$2,TariffTable!$B:$B,J$5)'
    ws[f"K{row}"] = f'=E{row}*H{row}+F{row}*I{row}+G{row}*J{row}'
    ws[f"L{row}"] = f'=IF(C{row}=0,0,K{row}/C{row})'
    ws[f"M{row}"] = f'=K{row}-D{row}'
    ws[f"N{row}"] = f'=IF(D{row}=0,0,M{row}/D{row})'
    ws[f"O{row}"] = f'=IF(M{row}>0,"OVER","WITHIN")'

ws["C3"] = "=SUM($K$7:$K$12)"
ws["E3"] = '=COUNTIF($O$7:$O$12,"OVER")'
ws["G3"] = "=MAX($M$7:$M$12)"

for row in range(18, 21):
    ws[f"A{row}"] = f'=ROWS($A$18:A{row})'
    ws[f"D{row}"] = f'=LARGE($M$7:$M$12,ROWS($D$18:D{row}))'
    ws[f"B{row}"] = f'=INDEX($A$7:$A$12,MATCH($D{row},$M$7:$M$12,0))'
    ws[f"C{row}"] = f'=INDEX($B$7:$B$12,MATCH($D{row},$M$7:$M$12,0))'
    ws[f"E{row}"] = f'=INDEX($N$7:$N$12,MATCH($D{row},$M$7:$M$12,0))'
    ws[f"F{row}"] = f'=INDEX($K$7:$K$12,MATCH($D{row},$M$7:$M$12,0))'
    ws[f"G{row}"] = f'=INDEX($L$7:$L$12,MATCH($D{row},$M$7:$M$12,0))'

wb.save(path)
wb.close()
PY

python3 /root/.codex/skills/xlsx/recalc.py /root/energy_budget_audit.xlsx 60
