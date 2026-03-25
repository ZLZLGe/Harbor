#!/bin/sh
set -eu

cat > /tmp/solve_transfer2.py <<'PY'
#!/usr/bin/env python3
import pandas as pd
from openpyxl import Workbook
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, SharedItems, WorksheetSource
from openpyxl.pivot.table import DataField, Location, PivotField, RowColField, TableDefinition

INPUT_FILE = "/root/retail_territory_input.xlsx"
OUTPUT_FILE = "/root/retail_margin_pack.xlsx"


def add_source_sheet(workbook: Workbook, df: pd.DataFrame, headers: list[str]) -> None:
    ws = workbook.active
    ws.title = "SourceData"
    ws.append(headers)
    for row in df[headers].itertuples(index=False):
        ws.append(list(row))


def make_cache(headers: list[str], num_rows: int) -> CacheDefinition:
    return CacheDefinition(
        cacheSource=CacheSource(
            type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:J{num_rows}", sheet="SourceData"),
        ),
        cacheFields=[CacheField(name=header, sharedItems=SharedItems()) for header in headers],
    )


def add_pivot(
    workbook: Workbook,
    headers: list[str],
    num_rows: int,
    *,
    sheet_name: str,
    table_name: str,
    row_field: str,
    data_field: str,
    subtotal: str,
    column_field: str | None = None,
) -> None:
    ws = workbook.create_sheet(sheet_name)
    row_idx = headers.index(row_field)
    data_idx = headers.index(data_field)
    col_idx = headers.index(column_field) if column_field else None
    pivot = TableDefinition(
        name=table_name,
        cacheId=0,
        dataCaption="Values",
        location=Location(
            ref="A3:F40" if column_field else "A3:C120",
            firstHeaderRow=1,
            firstDataRow=2 if column_field else 1,
            firstDataCol=1,
        ),
    )
    for i in range(len(headers)):
        axis = "axisRow" if i == row_idx else ("axisCol" if i == col_idx else None)
        pivot.pivotFields.append(PivotField(axis=axis, dataField=(i == data_idx), showAll=False))
    pivot.rowFields.append(RowColField(x=row_idx))
    if col_idx is not None:
        pivot.colFields.append(RowColField(x=col_idx))
    pivot.dataFields.append(DataField(name=table_name, fld=data_idx, subtotal=subtotal))
    pivot.cache = make_cache(headers, num_rows)
    ws._pivots.append(pivot)


def main() -> None:
    df = pd.read_excel(INPUT_FILE)
    numeric_cols = ["Orders", "Units", "AvgTicket", "ReturnRate", "PromoSpend"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["GrossRevenue"] = df["Orders"] * df["AvgTicket"]
    quartiles = df["ReturnRate"].quantile([0.25, 0.5, 0.75]).to_dict()

    def return_band(value: float) -> str:
        if value <= quartiles[0.25]:
            return "Q1"
        if value <= quartiles[0.5]:
            return "Q2"
        if value <= quartiles[0.75]:
            return "Q3"
        return "Q4"

    df["ReturnBand"] = df["ReturnRate"].apply(return_band)
    df["NetRevenue"] = (df["Orders"] * df["AvgTicket"] * (1 - df["ReturnRate"])) - df["PromoSpend"]

    headers = [
        "Territory",
        "StoreFormat",
        "Orders",
        "Units",
        "AvgTicket",
        "ReturnRate",
        "PromoSpend",
        "GrossRevenue",
        "ReturnBand",
        "NetRevenue",
    ]

    workbook = Workbook()
    add_source_sheet(workbook, df, headers)
    num_rows = len(df) + 1
    add_pivot(workbook, headers, num_rows, sheet_name="Orders by Territory", table_name="OrdersByTerritory", row_field="Territory", data_field="Orders", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Net Revenue by Format", table_name="NetRevenueByFormat", row_field="StoreFormat", data_field="NetRevenue", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Promo Spend by Territory", table_name="PromoSpendByTerritory", row_field="Territory", data_field="PromoSpend", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Net Revenue by Territory Band", table_name="NetRevenueByTerritoryBand", row_field="Territory", column_field="ReturnBand", data_field="NetRevenue", subtotal="sum")
    workbook.save(OUTPUT_FILE)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_transfer2.py
