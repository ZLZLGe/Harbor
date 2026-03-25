#!/bin/bash
set -euo pipefail

python3 <<'PY'
from openpyxl import load_workbook

wb = load_workbook("tourism_transfer_input.xlsx")
forecast = wb["Forecast"]

forecast["B3"] = "=(Actuals!B6/Actuals!B2)^(1/4)-1"
forecast["B4"] = "=(Actuals!C6/Actuals!C2)^(1/4)-1"

for forecast_row, project_row in zip(range(8, 13), range(2, 7)):
    forecast[f"A{forecast_row}"] = f"=Projects!A{project_row}"
    if forecast_row == 8:
        forecast[f"B{forecast_row}"] = "=Actuals!B6*(1+$B$3)"
        forecast[f"D{forecast_row}"] = "=Actuals!C6*(1+$B$4)"
    else:
        prev = forecast_row - 1
        forecast[f"B{forecast_row}"] = f"=B{prev}*(1+$B$3)"
        forecast[f"D{forecast_row}"] = f"=D{prev}*(1+$B$4)"
    forecast[f"C{forecast_row}"] = f"=B{forecast_row}*(1+Projects!B{project_row})"
    forecast[f"E{forecast_row}"] = f"=(Actuals!D6+SUM(Projects!C$2:C{project_row}))*$B$5"
    forecast[f"F{forecast_row}"] = f"=MIN(C{forecast_row},E{forecast_row})"
    forecast[f"G{forecast_row}"] = f"=F{forecast_row}*D{forecast_row}"

wb.save("tourism_transfer_completed.xlsx")
PY
