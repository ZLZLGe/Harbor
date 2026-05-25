#!/bin/bash

python3 <<'PYTHON'
import openpyxl

wb = openpyxl.load_workbook("transit_budget_incomplete.xlsx")
budget = wb["Operating Budget by Division"]
yoy = wb["YoY Changes (%)"]
shares = wb["Division Shares (%)"]
growth = wb["Growth Analysis"]

# Direct recoveries from row totals and cross-year arithmetic.
budget["K6"] = sum(budget.cell(row=6, column=col).value for col in range(2, 11))
budget["F8"] = budget["K8"].value - sum(
    budget.cell(row=8, column=col).value for col in range(2, 11) if col != 6
)
yoy["D7"] = round((budget["D8"].value - budget["D7"].value) / budget["D7"].value * 100, 2)
growth["H7"] = budget["H13"].value - budget["H8"].value

# Recover values that depend on already-known totals or YoY rates.
budget["B9"] = round(budget["B8"].value * (1 + yoy["B8"].value / 100))
budget["C12"] = round(budget["C11"].value * (1 + yoy["C11"].value / 100))
budget["K10"] = round(budget["K9"].value * (1 + yoy["K9"].value / 100))
yoy["F8"] = round((budget["F9"].value - budget["F8"].value) / budget["F8"].value * 100, 2)
shares["F5"] = round(budget["F5"].value / budget["K5"].value * 100, 2)

# Longer chains across sheets.
budget["E10"] = round(budget["K10"].value * shares["E10"].value / 100)
yoy["B9"] = round((budget["B10"].value - budget["B9"].value) / budget["B9"].value * 100, 2)
shares["B10"] = round(budget["B10"].value / budget["K10"].value * 100, 2)
growth["B8"] = round(
    (
        budget["B8"].value
        + budget["B9"].value
        + budget["B10"].value
        + budget["B11"].value
        + budget["B12"].value
        + budget["B13"].value
    )
    / 6,
    1,
)

# Cross-sheet trend checks.
growth["E4"] = round(((budget["E13"].value / budget["E8"].value) ** 0.2 - 1) * 100, 2)
growth["E5"] = budget["E8"].value

wb.save("transit_budget_recovered.xlsx")
print("Recovered 15 missing values in transit_budget_recovered.xlsx")
PYTHON
