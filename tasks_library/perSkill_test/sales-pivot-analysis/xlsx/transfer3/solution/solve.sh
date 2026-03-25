#!/bin/sh
set -eu

cat > /tmp/solve_transfer3.py <<'PY'
#!/usr/bin/env python3
import pandas as pd
from openpyxl import Workbook
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, SharedItems, WorksheetSource
from openpyxl.pivot.table import DataField, Location, PivotField, RowColField, TableDefinition

INPUT_FILE = "/root/training_program_input.xlsx"
OUTPUT_FILE = "/root/training_grant_dashboard.xlsx"


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
            worksheetSource=WorksheetSource(ref=f"A1:I{num_rows}", sheet="SourceData"),
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
    numeric_cols = ["Participants", "CompletionRate", "GrantPerParticipant", "MentorHours"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["CompletedParticipants"] = (df["Participants"] * df["CompletionRate"]).round().astype(int)
    quartiles = df["CompletionRate"].quantile([0.25, 0.5, 0.75]).to_dict()

    def completion_band(value: float) -> str:
        if value <= quartiles[0.25]:
            return "Q1"
        if value <= quartiles[0.5]:
            return "Q2"
        if value <= quartiles[0.75]:
            return "Q3"
        return "Q4"

    df["CompletionBand"] = df["CompletionRate"].apply(completion_band)
    df["GrantSpend"] = df["Participants"] * df["GrantPerParticipant"]

    headers = [
        "ProgramRegion",
        "CourseTrack",
        "Participants",
        "CompletionRate",
        "GrantPerParticipant",
        "MentorHours",
        "CompletedParticipants",
        "CompletionBand",
        "GrantSpend",
    ]

    workbook = Workbook()
    add_source_sheet(workbook, df, headers)
    num_rows = len(df) + 1
    add_pivot(workbook, headers, num_rows, sheet_name="Participants by Region", table_name="ParticipantsByRegion", row_field="ProgramRegion", data_field="Participants", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Completed by Track", table_name="CompletedByTrack", row_field="CourseTrack", data_field="CompletedParticipants", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Grant Spend by Region", table_name="GrantSpendByRegion", row_field="ProgramRegion", data_field="GrantSpend", subtotal="sum")
    add_pivot(workbook, headers, num_rows, sheet_name="Grant Spend by Region Band", table_name="GrantSpendByRegionBand", row_field="ProgramRegion", column_field="CompletionBand", data_field="GrantSpend", subtotal="sum")
    workbook.save(OUTPUT_FILE)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_transfer3.py
