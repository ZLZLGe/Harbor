#!/bin/bash
set -euo pipefail

python3 <<'PY'
from openpyxl import load_workbook

wb = load_workbook("energy_transfer_input.xlsx")
results = wb["Results"]

results["B3"] = "=(Actuals!B6/Actuals!B2)^(1/4)-1"
results["B4"] = "=(Actuals!C6/Actuals!C2)^(1/4)-1"
results["B5"] = "=AVERAGE(Actuals!D4:D6)"

for result_row, upgrade_row in zip(range(8, 13), range(2, 7)):
    results[f"A{result_row}"] = f"=Upgrade!A{upgrade_row}"
    if result_row == 8:
        results[f"B{result_row}"] = "=Actuals!B6*(1+$B$3)"
        results[f"E{result_row}"] = "=Actuals!C6*(1+$B$4)"
        results[f"H{result_row}"] = "=G8"
    else:
        prev = result_row - 1
        results[f"B{result_row}"] = f"=B{prev}*(1+$B$3)"
        results[f"E{result_row}"] = f"=E{prev}*(1+$B$4)"
        results[f"H{result_row}"] = f"=H{prev}+G{result_row}"
    results[f"C{result_row}"] = f"=B{result_row}*(1-$B$5)"
    results[f"D{result_row}"] = f"=B{result_row}*(1-Upgrade!B{upgrade_row})"
    results[f"F{result_row}"] = f"=(D{result_row}-C{result_row})*E{result_row}"
    results[f"G{result_row}"] = f"=F{result_row}-Upgrade!C{upgrade_row}"

wb.save("energy_transfer_completed.xlsx")
PY
