#!/bin/bash
set -euo pipefail

python3 <<'PY'
from openpyxl import load_workbook

wb = load_workbook("manufacturer_similar_input.xlsx")
dep = wb["Depreciation"]
for row in range(2, 10):
    dep[f"D{row}"] = f"=B{row}/C{row}"

model = wb["Model"]
for model_row, src_row in zip(range(7, 15), range(2, 10)):
    model[f"A{model_row}"] = f"=Historical!A{src_row}"
    model[f"B{model_row}"] = f"=Historical!B{src_row}"
    model[f"C{model_row}"] = f"=Historical!C{src_row}"
    model[f"D{model_row}"] = f"=Historical!D{src_row}"
    model[f"E{model_row}"] = f"=LN(B{model_row})"
    model[f"F{model_row}"] = f"=LN(C{model_row})"
    model[f"G{model_row}"] = (
        f"=C{model_row}/((B{model_row}^Assumptions!$B$2)*(D{model_row}^(1-Assumptions!$B$2)))"
    )

model["B3"] = "=AVERAGE(Depreciation!D6:D9)"
model["G17"] = "=AVERAGE(G11:G14)"

for model_row, shock_row in zip(range(20, 28), range(2, 10)):
    model[f"A{model_row}"] = f"=Shock!A{shock_row}"
    if model_row == 20:
        model[f"B{model_row}"] = "=B14*(1-$B$3)"
        model[f"C{model_row}"] = f"=B14*(1-$B$3)+Shock!B{shock_row}"
    else:
        prev = model_row - 1
        model[f"B{model_row}"] = f"=B{prev}*(1-$B$3)"
        model[f"C{model_row}"] = f"=C{prev}*(1-$B$3)+Shock!B{shock_row}"
    model[f"D{model_row}"] = (
        f"=$G$17*((B{model_row}^Assumptions!$B$2)*(Assumptions!$B$3^(1-Assumptions!$B$2)))"
    )
    model[f"E{model_row}"] = (
        f"=$G$17*((C{model_row}^Assumptions!$B$2)*(Assumptions!$B$3^(1-Assumptions!$B$2)))"
    )

wb.save("manufacturer_similar_completed.xlsx")
PY
