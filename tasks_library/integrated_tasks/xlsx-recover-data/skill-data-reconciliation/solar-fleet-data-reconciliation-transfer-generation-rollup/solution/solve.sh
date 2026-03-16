#!/bin/bash

python3 <<'PYTHON'
import openpyxl

wb = openpyxl.load_workbook("solar_generation_incomplete.xlsx")
generation = wb["Monthly Generation (MWh)"]
outage = wb["Outage Impact (%)"]
shares = wb["Site Contribution (%)"]
annual = wb["Annual Capacity Review"]

# Recover monthly generation values from row and column totals.
generation["C6"] = generation["F6"].value - sum(generation[cell].value for cell in ["B6", "D6", "E6"])
generation["D7"] = generation["F7"].value - sum(generation[cell].value for cell in ["B7", "C7", "E7"])
generation["E8"] = generation["F8"].value - sum(generation[cell].value for cell in ["B8", "C8", "D8"])
generation["B10"] = sum(generation[f"B{row}"].value for row in range(5, 9))
generation["F10"] = sum(generation[f"{col}10"].value for col in "BCDE")

# Recover outage ratios using nominal monthly output from the annual review.
outage["D5"] = round((1 - generation["D5"].value / annual["C7"].value) * 100, 2)
outage["B6"] = round((1 - generation["B6"].value / annual["C5"].value) * 100, 2)
outage["E7"] = round((1 - generation["E7"].value / annual["C8"].value) * 100, 2)
outage["F8"] = round((1 - generation["F8"].value / annual["C9"].value) * 100, 2)

# Recover site contribution percentages from monthly totals.
shares["B5"] = round(generation["B5"].value / generation["F5"].value * 100, 2)
shares["C6"] = round(generation["C6"].value / generation["F6"].value * 100, 2)
shares["D7"] = round(generation["D7"].value / generation["F7"].value * 100, 2)
shares["E8"] = round(generation["E8"].value / generation["F8"].value * 100, 2)

# Recover annual review metrics from monthly rollups.
annual["E5"] = generation["B10"].value
annual["F6"] = annual["D6"].value - annual["E6"].value
annual["I7"] = round(annual["E7"].value / annual["E9"].value * 100, 2)
annual["G8"] = round(annual["E8"].value / annual["D8"].value * 100, 2)
annual["H9"] = round(annual["E9"].value / 4, 2)

wb.save("solar_generation_reconciled.xlsx")
print("Recovered 18 missing values in solar_generation_reconciled.xlsx")
PYTHON
