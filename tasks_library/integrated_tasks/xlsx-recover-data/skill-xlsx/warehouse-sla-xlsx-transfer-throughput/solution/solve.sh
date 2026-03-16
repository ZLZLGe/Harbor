#!/bin/bash

python3 <<'PYTHON'
import openpyxl

INPUT_FILE = "warehouse_sla_incomplete.xlsx"
OUTPUT_FILE = "warehouse_sla_completed.xlsx"

wb = openpyxl.load_workbook(INPUT_FILE)
budget = wb["Throughput Plan"]
yoy = wb["SLA Changes (%)"]
shares = wb["Lane Shares (%)"]
review = wb["Capacity Review"]

budget["F8"] = budget["K8"].value - sum(
    budget.cell(row=8, column=col).value for col in range(2, 11) if col != 6
)
budget["K5"] = sum(budget.cell(row=5, column=col).value for col in range(2, 11))
yoy["D7"] = round((budget["D8"].value - budget["D7"].value) / budget["D7"].value * 100, 2)
review["B7"] = review["B6"].value - review["B5"].value

budget["B9"] = round(budget["B8"].value * (1 + yoy["B8"].value / 100))
budget["C12"] = round(budget["C11"].value * (1 + yoy["C11"].value / 100))
budget["K10"] = round(budget["K9"].value * (1 + yoy["K9"].value / 100))
yoy["F9"] = round((budget["F10"].value - budget["F9"].value) / budget["F9"].value * 100, 2)
shares["F5"] = round(budget["F5"].value / budget["K5"].value * 100, 2)

budget["E10"] = round(budget["K10"].value * shares["E10"].value / 100)
yoy["B9"] = round((budget["B10"].value - budget["B9"].value) / budget["B9"].value * 100, 2)
shares["B10"] = round(budget["B10"].value / budget["K10"].value * 100, 2)
review["B8"] = round(sum(budget[f"B{row}"].value for row in range(8, 14)) / 6, 1)

review["E5"] = budget["E8"].value
review["E4"] = round(((review["E6"].value / review["E5"].value) ** 0.2 - 1) * 100, 2)

wb.save(OUTPUT_FILE)
print("Recovered 15 missing values in the warehouse SLA workbook")
PYTHON
