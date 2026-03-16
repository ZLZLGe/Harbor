#!/bin/bash

python3 <<'PYTHON'
import openpyxl

wb = openpyxl.load_workbook("warehouse_inventory_incomplete.xlsx")
inventory = wb["Ending Inventory by Warehouse"]
flow = wb["Inbound-Outbound Flow"]
shares = wb["Warehouse Shares (%)"]
shrink = wb["Shrinkage Analysis"]

# Direct recoveries from row totals and movement equations.
inventory["F5"] = inventory["G5"].value - sum(
    inventory.cell(row=5, column=col).value for col in range(2, 6)
)
flow["F6"] = flow["B6"].value + flow["C6"].value - flow["D6"].value - flow["E6"].value
flow["F9"] = flow["B9"].value + flow["C9"].value - flow["D9"].value - flow["E9"].value
flow["C10"] = flow["F10"].value - flow["B10"].value + flow["D10"].value + flow["E10"].value

# Recover dependent values across ledger and share sheets.
flow["B7"] = flow["F6"].value
inventory["G7"] = flow["F7"].value
shares["F5"] = round(inventory["F5"].value / inventory["G5"].value * 100, 2)
shares["C7"] = round(inventory["C7"].value / inventory["G7"].value * 100, 2)
inventory["C8"] = round(inventory["G8"].value * shares["C8"].value / 100)
inventory["G9"] = flow["F9"].value
inventory["B9"] = round(inventory["G9"].value * shares["B9"].value / 100)
inventory["E10"] = round(inventory["G10"].value * shares["E10"].value / 100)
shares["D10"] = round(inventory["D10"].value / inventory["G10"].value * 100, 2)

# Final audit checks from the shrinkage analysis sheet.
shrink["D8"] = inventory["D10"].value - inventory["D5"].value
shrink["B9"] = round(
    sum(inventory.cell(row=row, column=2).value for row in range(5, 11)) / 6,
    1,
)

wb.save("warehouse_inventory_reconciled.xlsx")
print("Recovered 15 missing values in warehouse_inventory_reconciled.xlsx")
PYTHON
