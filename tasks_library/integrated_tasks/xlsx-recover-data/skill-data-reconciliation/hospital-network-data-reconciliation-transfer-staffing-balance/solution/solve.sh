#!/bin/bash

python3 <<'PYTHON'
import openpyxl

wb = openpyxl.load_workbook("hospital_staffing_incomplete.xlsx")
staffing = wb["Quarterly Staffing"]
movement = wb["Recruitment & Attrition"]
shares = wb["FTE Shares (%)"]
overview = wb["Annual Workforce Overview"]

# Direct recoveries from quarter totals and movement arithmetic.
staffing["F5"] = staffing["G5"].value - sum(
    staffing.cell(row=5, column=col).value for col in range(2, 6)
)
staffing["G6"] = sum(staffing.cell(row=6, column=col).value for col in range(2, 7))
movement["C5"] = movement["E5"].value - movement["B5"].value + movement["D5"].value
movement["E6"] = movement["B6"].value + movement["C6"].value - movement["D6"].value
movement["F8"] = round(
    (movement["E8"].value - movement["B8"].value) / movement["B8"].value * 100,
    2,
)

# Dependent recoveries across sheets.
movement["B7"] = movement["E6"].value
movement["D7"] = movement["B7"].value + movement["C7"].value - movement["E7"].value
shares["F5"] = round(staffing["F5"].value / staffing["G5"].value * 100, 2)
shares["D6"] = round(staffing["D6"].value / staffing["G6"].value * 100, 2)
shares["E7"] = round(staffing["E7"].value / staffing["G7"].value * 100, 2)
staffing["C7"] = round(staffing["G7"].value * shares["C7"].value / 100)
staffing["B8"] = round(staffing["G8"].value * shares["B8"].value / 100)

# Annual overview roll-up checks.
overview["G6"] = overview["E6"].value - overview["B6"].value
overview["F7"] = round(
    sum(overview.cell(row=7, column=col).value for col in range(2, 6)) / 4,
    2,
)
overview["B10"] = staffing["G5"].value

wb.save("hospital_staffing_reconciled.xlsx")
print("Recovered 15 missing values in hospital_staffing_reconciled.xlsx")
PYTHON
