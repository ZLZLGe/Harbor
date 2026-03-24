#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

from openpyxl import load_workbook


def find_template() -> Path:
    matches = sorted(Path("/root").glob("tourism-capacity-template*"))
    if not matches:
        raise FileNotFoundError("未找到 tourism-capacity-template 前缀的模板工作簿")
    return matches[0]


template_path = find_template()
output_path = Path("/root") / f"tourism-capacity-shock{template_path.suffix}"

wb = load_workbook(template_path)

capital = wb["Tourism_Capital"]
capital["B3"] = "=AVERAGE(C8:C13)"
for row in range(14, 19):
    capital[f"C{row}"] = "=$B$3"
for row in range(8, 14):
    capital[f"D{row}"] = "=0"
for row in range(14, 19):
    capital[f"D{row}"] = f"=Expansion_Plan!B{row - 6}"
for row in range(8, 19):
    capital[f"E{row}"] = f"=B{row}+D{row}"
    capital[f"F{row}"] = f"=D{row}*$B$2"

spend = wb["Visitor_Spend"]
for row in range(8, 14):
    spend[f"D{row}"] = f"=C{row}"
for row in range(14, 19):
    spend[f"D{row}"] = f"=D{row - 1}*(1+$B$2)"
for row in range(8, 19):
    spend[f"E{row}"] = f"=D{row}*$B$3"

expansion = wb["Expansion_Plan"]
for row in range(8, 13):
    expansion[f"C{row}"] = f"=SUM($B$8:B{row})"

demand = wb["Demand_Forecast"]
for row in range(8, 14):
    demand[f"B{row}"] = f"=Visitor_Spend!B{row}"
for row in range(14, 19):
    demand[f"B{row}"] = f"=TREND($B$8:$B$13,$A$8:$A$13,A{row})"
for row in range(8, 19):
    demand[f"C{row}"] = f"=Tourism_Capital!B{row}*365*Tourism_Capital!C{row}"
    demand[f"D{row}"] = f"=MIN(B{row},C{row})"
    demand[f"F{row}"] = f"=Tourism_Capital!E{row}*365*Tourism_Capital!C{row}"
    demand[f"G{row}"] = f"=MIN(E{row},F{row})"
for row in range(8, 14):
    demand[f"E{row}"] = f"=B{row}"
for row in range(14, 19):
    demand[f"E{row}"] = f"=B{row}*(1+$B$2)"

revenue = wb["Revenue_Model"]
for model_row, demand_row in zip(range(8, 15), range(12, 19)):
    revenue[f"B{model_row}"] = f"=Demand_Forecast!D{demand_row}"
    revenue[f"C{model_row}"] = f"=Demand_Forecast!G{demand_row}"
    revenue[f"D{model_row}"] = f"=Visitor_Spend!E{demand_row}"
    revenue[f"E{model_row}"] = f"=B{model_row}*D{model_row}"
    revenue[f"F{model_row}"] = f"=C{model_row}*D{model_row}"
    revenue[f"G{model_row}"] = f"=F{model_row}-E{model_row}"
    revenue[f"H{model_row}"] = f"=Tourism_Capital!F{demand_row}"
    revenue[f"I{model_row}"] = f'=IF(H{model_row}=0,"",G{model_row}/H{model_row})'

wb.save(output_path)
PY
