#!/bin/bash
set -e

cat > /tmp/solve_warehouse_restock_analysis.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3

from __future__ import annotations

import pandas as pd
from openpyxl import Workbook
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, SharedItems, WorksheetSource
from openpyxl.pivot.table import DataField, Location, PivotField, RowColField, TableDefinition

OUTPUT_FILE = "/root/warehouse_restock_analysis.xlsx"
INVENTORY_FILE = "/root/warehouse_inventory.xlsx"
RULES_FILE = "/root/restock_rules.xlsx"

HEADERS = [
    "BatchID",
    "Warehouse",
    "SKU",
    "ItemName",
    "Category",
    "ReceivedDate",
    "AsOfDate",
    "AgeDays",
    "AgingBucket",
    "OnHandUnits",
    "UnitCost",
    "InventoryValue",
    "WeeklyDemand",
    "WeeksCover",
    "TargetWeeksCover",
    "SafetyWeeks",
    "GapToTargetUnits",
    "TurnoverRisk",
    "RestockPriority",
]

PRIORITY_ORDER = {"Urgent": 0, "Replenish": 1, "Normal": 2, "Hold": 3, "Monitor": 4}


def normalize_warehouse(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.title()


def normalize_sku(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def aging_bucket(age_days: int) -> str:
    if age_days <= 30:
        return "0-30"
    if age_days <= 60:
        return "31-60"
    if age_days <= 90:
        return "61-90"
    if age_days <= 180:
        return "91-180"
    return "181+"


def turnover_risk(row: pd.Series) -> str:
    if row["WeeklyDemand"] == 0:
        return "Dormant"
    if row["AgeDays"] > row["CriticalAgingDays"] and row["WeeksCover"] > row["TargetWeeksCover"]:
        return "Critical Aging"
    if row["WeeksCover"] < row["SafetyWeeks"]:
        return "Low Cover"
    if row["WeeksCover"] > row["TargetWeeksCover"] * 1.5:
        return "Excess Cover"
    return "Healthy"


def restock_priority(row: pd.Series) -> str:
    if row["WeeklyDemand"] == 0:
        return "Monitor"
    if row["WeeksCover"] < row["SafetyWeeks"]:
        return "Urgent"
    if row["GapToTargetUnits"] > 0:
        return "Replenish"
    if row["TurnoverRisk"] in {"Critical Aging", "Excess Cover"}:
        return "Hold"
    return "Normal"


ledger = pd.read_excel(INVENTORY_FILE, sheet_name="Ledger")
products = pd.read_excel(INVENTORY_FILE, sheet_name="Products")
demand = pd.read_excel(RULES_FILE, sheet_name="DemandPlan")
policy = pd.read_excel(RULES_FILE, sheet_name="Policy")
parameters = pd.read_excel(RULES_FILE, sheet_name="Parameters")

for frame in (ledger, demand):
    frame["Warehouse"] = normalize_warehouse(frame["Warehouse"])
    frame["SKU"] = normalize_sku(frame["SKU"])

products["SKU"] = normalize_sku(products["SKU"])
products["Category"] = products["Category"].astype(str).str.strip()
products["ItemName"] = products["ItemName"].astype(str).str.strip()
policy["Category"] = policy["Category"].astype(str).str.strip()

ledger["ReceivedDate"] = pd.to_datetime(ledger["ReceivedDate"])
as_of_date = pd.to_datetime(
    parameters.loc[parameters["Parameter"].astype(str).str.strip() == "AsOfDate", "Value"].iloc[0]
)

detail = ledger.merge(products, on="SKU", how="left").merge(
    demand,
    on=["Warehouse", "SKU"],
    how="left",
).merge(
    policy,
    on="Category",
    how="left",
)

detail["AgeDays"] = (as_of_date - detail["ReceivedDate"]).dt.days.astype(int)
detail["AgingBucket"] = detail["AgeDays"].apply(aging_bucket)
detail["InventoryValue"] = (detail["OnHandUnits"] * detail["UnitCost"]).round(2)
detail["WeeksCover"] = detail.apply(
    lambda row: round(row["OnHandUnits"] / row["WeeklyDemand"], 2) if row["WeeklyDemand"] else 0.0,
    axis=1,
)
detail["GapToTargetUnits"] = (
    (detail["TargetWeeksCover"] * detail["WeeklyDemand"] - detail["OnHandUnits"])
    .clip(lower=0)
    .astype(int)
)
detail["TurnoverRisk"] = detail.apply(turnover_risk, axis=1)
detail["RestockPriority"] = detail.apply(restock_priority, axis=1)
detail["ReceivedDate"] = detail["ReceivedDate"].dt.strftime("%Y-%m-%d")
detail["AsOfDate"] = as_of_date.strftime("%Y-%m-%d")
detail["priority_order"] = detail["RestockPriority"].map(PRIORITY_ORDER)
detail = detail.sort_values(["Warehouse", "priority_order", "AgeDays", "BatchID"], ascending=[True, True, False, True])
detail = detail.drop(columns=["priority_order"]).reset_index(drop=True)
detail = detail[HEADERS]

workbook = Workbook()
detail_sheet = workbook.active
detail_sheet.title = "InventoryDetail"
detail_sheet.append(HEADERS)
for row in detail.itertuples(index=False):
    detail_sheet.append(list(row))


def make_cache(num_rows: int) -> CacheDefinition:
    return CacheDefinition(
        cacheSource=CacheSource(
            type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:S{num_rows}", sheet="InventoryDetail"),
        ),
        cacheFields=[CacheField(name=header, sharedItems=SharedItems()) for header in HEADERS],
    )


def add_pivot(sheet_name: str, pivot_name: str, row_idx: int, data_idx: int, subtotal: str, col_idx: int | None = None) -> None:
    pivot_sheet = workbook.create_sheet(sheet_name)
    pivot = TableDefinition(
        name=pivot_name,
        cacheId=0,
        dataCaption=subtotal.title(),
        location=Location(
            ref="A3:G18" if col_idx is not None else "A3:B18",
            firstHeaderRow=1,
            firstDataRow=2 if col_idx is not None else 1,
            firstDataCol=1,
        ),
    )
    for index in range(len(HEADERS)):
        axis = "axisRow" if index == row_idx else ("axisCol" if index == col_idx else None)
        pivot.pivotFields.append(PivotField(axis=axis, dataField=(index == data_idx), showAll=False))
    pivot.rowFields.append(RowColField(x=row_idx))
    if col_idx is not None:
        pivot.colFields.append(RowColField(x=col_idx))
    pivot.dataFields.append(DataField(name=pivot_name, fld=data_idx, subtotal=subtotal))
    pivot.cache = make_cache(len(detail) + 1)
    pivot_sheet._pivots.append(pivot)


add_pivot("Warehouse Value", "WarehouseValue", row_idx=1, data_idx=11, subtotal="sum")
add_pivot("Category Aging", "CategoryAging", row_idx=4, data_idx=9, subtotal="sum", col_idx=8)
add_pivot("Priority Gap", "PriorityGap", row_idx=18, data_idx=16, subtotal="sum")
add_pivot("Warehouse Priority Matrix", "WarehousePriorityMatrix", row_idx=1, data_idx=11, subtotal="sum", col_idx=18)

workbook.save(OUTPUT_FILE)
PYTHON_SCRIPT

python3 /tmp/solve_warehouse_restock_analysis.py
