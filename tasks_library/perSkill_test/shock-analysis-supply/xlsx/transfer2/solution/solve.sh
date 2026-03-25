#!/bin/bash
set -euo pipefail

python3 <<'PY'
from openpyxl import load_workbook

wb = load_workbook("port_transfer_input.xlsx")
model = wb["Model"]

model["B3"] = "=(Actuals!B6/Actuals!B2)^(1/4)-1"
model["B4"] = "=(Actuals!C6/Actuals!C2)^(1/4)-1"

for model_row, expansion_row in zip(range(8, 13), range(2, 7)):
    model[f"A{model_row}"] = f"=Expansion!A{expansion_row}"
    if model_row == 8:
        model[f"B{model_row}"] = "=Actuals!B6*(1+$B$3)"
        model[f"F{model_row}"] = "=Actuals!C6*(1+$B$4)"
    else:
        prev = model_row - 1
        model[f"B{model_row}"] = f"=B{prev}*(1+$B$3)"
        model[f"F{model_row}"] = f"=F{prev}*(1+$B$4)"
    model[f"C{model_row}"] = f"=Actuals!D6+SUM(Expansion!B$2:B{expansion_row})"
    model[f"D{model_row}"] = f"=C{model_row}*$B$5*(1+Expansion!C{expansion_row})"
    model[f"E{model_row}"] = f"=MIN(B{model_row},D{model_row})"
    model[f"G{model_row}"] = f"=E{model_row}*F{model_row}"
    model[f"H{model_row}"] = f"=D{model_row}-B{model_row}"

wb.save("port_transfer_completed.xlsx")
PY
