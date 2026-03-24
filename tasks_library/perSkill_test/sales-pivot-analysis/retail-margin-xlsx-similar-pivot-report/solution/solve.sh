#!/bin/bash
set -euo pipefail

cat > /tmp/build_retail_margin_report.py <<'PY'
#!/usr/bin/env python3
import pandas as pd
from openpyxl import Workbook
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, SharedItems, WorksheetSource
from openpyxl.pivot.table import DataField, Location, PivotField, RowColField, TableDefinition

OUTPUT_FILE = "/root/retail_margin_report.xlsx"
SALES_FILE = "/root/sales_transactions.xlsx"
PRODUCT_FILE = "/root/product_master.xlsx"

HEADERS = [
    "OrderID",
    "OrderDate",
    "Region",
    "Channel",
    "SKU",
    "Category",
    "Units",
    "UnitPrice",
    "DiscountPct",
    "UnitCost",
    "GrossSales",
    "NetSales",
    "TotalCost",
    "GrossProfit",
    "DiscountBand",
]


def normalize_sales_frame() -> pd.DataFrame:
    sales = pd.read_excel(SALES_FILE)
    products = pd.read_excel(PRODUCT_FILE)

    sales["SKU"] = sales["SKU"].astype(str).str.strip().str.upper()
    sales["Region"] = sales["Region"].astype(str).str.strip().str.title()
    sales["Channel"] = sales["Channel"].astype(str).str.strip().str.title()
    sales["OrderDate"] = sales["OrderDate"].astype(str).str.strip()

    for column in ["Units", "UnitPrice", "DiscountPct"]:
        sales[column] = pd.to_numeric(sales[column], errors="raise")

    products["SKU"] = products["SKU"].astype(str).str.strip().str.upper()
    products["Category"] = products["Category"].astype(str).str.strip()
    products["UnitCost"] = pd.to_numeric(products["UnitCost"], errors="raise")

    merged = sales.merge(products[["SKU", "Category", "UnitCost"]], on="SKU", how="inner")

    merged["GrossSales"] = (merged["Units"] * merged["UnitPrice"]).round(2)
    merged["NetSales"] = (merged["GrossSales"] * (1 - merged["DiscountPct"])).round(2)
    merged["TotalCost"] = (merged["Units"] * merged["UnitCost"]).round(2)
    merged["GrossProfit"] = (merged["NetSales"] - merged["TotalCost"]).round(2)

    def discount_band(value: float) -> str:
        if value == 0:
            return "No Discount"
        if value < 0.10:
            return "1-9%"
        if value < 0.20:
            return "10-19%"
        return "20%+"

    merged["DiscountBand"] = merged["DiscountPct"].apply(discount_band)
    return merged[HEADERS]


def make_cache(num_rows: int) -> CacheDefinition:
    return CacheDefinition(
        cacheSource=CacheSource(
            type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:O{num_rows}", sheet="SourceData"),
        ),
        cacheFields=[CacheField(name=header, sharedItems=SharedItems()) for header in HEADERS],
    )


def add_pivot_sheet(
    workbook: Workbook,
    dataframe: pd.DataFrame,
    sheet_name: str,
    pivot_name: str,
    row_idx: int,
    data_idx: int,
    subtotal: str,
    col_idx: int | None = None,
) -> None:
    sheet = workbook.create_sheet(sheet_name)
    location_ref = "A3:F20" if col_idx is not None else "A3:B20"
    pivot = TableDefinition(
        name=pivot_name,
        cacheId=0,
        dataCaption="Values",
        location=Location(
            ref=location_ref,
            firstHeaderRow=1,
            firstDataRow=1 if col_idx is None else 2,
            firstDataCol=1,
        ),
    )

    for index in range(len(HEADERS)):
        axis = "axisRow" if index == row_idx else "axisCol" if index == col_idx else None
        pivot.pivotFields.append(PivotField(axis=axis, dataField=(index == data_idx), showAll=False))

    pivot.rowFields.append(RowColField(x=row_idx))
    if col_idx is not None:
        pivot.colFields.append(RowColField(x=col_idx))
    pivot.dataFields.append(DataField(name=pivot_name, fld=data_idx, subtotal=subtotal))
    pivot.cache = make_cache(len(dataframe) + 1)
    sheet._pivots.append(pivot)


def main() -> None:
    dataframe = normalize_sales_frame()

    workbook = Workbook()
    source_sheet = workbook.active
    source_sheet.title = "SourceData"
    source_sheet.append(HEADERS)
    for row in dataframe.itertuples(index=False, name=None):
        source_sheet.append(list(row))

    add_pivot_sheet(workbook, dataframe, "Margin by Region", "GrossProfitByRegion", 2, 13, "sum")
    add_pivot_sheet(workbook, dataframe, "Margin by Category", "GrossProfitByCategory", 5, 13, "sum")
    add_pivot_sheet(workbook, dataframe, "Net Sales by Channel", "NetSalesByChannel", 3, 11, "sum")
    add_pivot_sheet(workbook, dataframe, "Discount Band Profit", "GrossProfitByBandAndChannel", 14, 13, "sum", col_idx=3)

    workbook.save(OUTPUT_FILE)


if __name__ == "__main__":
    main()
PY

python3 /tmp/build_retail_margin_report.py
