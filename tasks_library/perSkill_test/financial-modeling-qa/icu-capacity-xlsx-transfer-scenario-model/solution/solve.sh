#!/bin/bash
set -e

python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape

INPUT_PATH = Path("/root/icu_capacity_template.xlsx")
OUTPUT_PATH = Path("/root/ward_capacity_model.xlsx")


def col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def cell(ref: str, kind: str, value=None, style: int | None = None, formula: str | None = None):
    return {"ref": ref, "kind": kind, "value": value, "style": style, "formula": formula}


def build_sheet(cells, merges=None, col_widths=None, dimension="A1:A1", freeze=None):
    merges = merges or []
    col_widths = col_widths or {}
    rows = {}
    for item in cells:
        row_num = int("".join(ch for ch in item["ref"] if ch.isdigit()))
        rows.setdefault(row_num, []).append(item)

    def sort_key(item):
        ref = item["ref"]
        col = "".join(ch for ch in ref if ch.isalpha())
        value = 0
        for ch in col:
            value = value * 26 + ord(ch) - 64
        return value

    row_xml = []
    for row_num in sorted(rows):
        cell_xml = []
        for item in sorted(rows[row_num], key=sort_key):
            attrs = [f'r="{item["ref"]}"']
            if item["style"] is not None:
                attrs.append(f's="{item["style"]}"')
            if item["kind"] == "str":
                attrs.append('t="inlineStr"')
                value = escape(str(item["value"]))
                cell_xml.append(f'<c {" ".join(attrs)}><is><t>{value}</t></is></c>')
            elif item["kind"] == "num":
                cell_xml.append(f'<c {" ".join(attrs)}><v>{item["value"]}</v></c>')
            elif item["kind"] == "formula":
                value_xml = "" if item["value"] is None else f"<v>{item['value']}</v>"
                cell_xml.append(
                    f'<c {" ".join(attrs)}><f>{escape(item["formula"])}</f>{value_xml}</c>'
                )
            elif item["kind"] == "blank":
                cell_xml.append(f'<c {" ".join(attrs)}/>')
            else:
                raise ValueError(item["kind"])
        row_xml.append(f'<row r="{row_num}">{"".join(cell_xml)}</row>')

    cols_xml = ""
    if col_widths:
        cols = []
        for idx, width in sorted(col_widths.items()):
            cols.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
        cols_xml = "<cols>" + "".join(cols) + "</cols>"

    merge_xml = ""
    if merges:
        merge_xml = (
            f'<mergeCells count="{len(merges)}">'
            + "".join(f'<mergeCell ref="{item}"/>' for item in merges)
            + "</mergeCells>"
        )

    sheet_views = '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
    if freeze:
        y_split, top_left = freeze
        sheet_views = (
            '<sheetViews><sheetView workbookViewId="0">'
            f'<pane ySplit="{y_split}" topLeftCell="{top_left}" activePane="bottomLeft" state="frozen"/>'
            f'<selection pane="bottomLeft" activeCell="{top_left}" sqref="{top_left}"/>'
            "</sheetView></sheetViews>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        f"{sheet_views}"
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"{cols_xml}"
        "<sheetData>"
        + "".join(row_xml)
        + "</sheetData>"
        + merge_xml
        + "</worksheet>"
    )


ward_rows = [
    ("Medical ICU", 24, 20, 17, 0.30),
    ("Surgical ICU", 18, 16, 13, 0.22),
    ("Cardiac ICU", 16, 14, 12, 0.18),
    ("Neuro ICU", 14, 12, 9, 0.15),
    ("Stepdown Flex", 12, 10, 7, 0.15),
]
scenario_cols = [("F", "I", "B"), ("G", "J", "C"), ("H", "K", "D")]

ward_headers = [
    "Unit",
    "Licensed Beds",
    "Staffed Beds",
    "Local Census",
    "Transfer Share",
    "Baseline Census",
    "Transfer Surge Census",
    "Flu Crisis Census",
    "Baseline Occupancy",
    "Transfer Surge Occupancy",
    "Flu Crisis Occupancy",
]

ward_values = {
    "F": [17, 13, 12, 9, 7],
    "G": [20, 16, 14, 11, 9],
    "H": [20, 16, 14, 12, 10],
    "I": [0.85, 0.8125, 0.8571428571, 0.75, 0.7],
    "J": [1, 1, 1, 0.9166666667, 0.9],
    "K": [1, 1, 1, 1, 1],
}

ward_cells = [
    cell("A1", "str", "Ward Load and Scenario Census", 1),
    cell(
        "A3",
        "str",
        "Complete the yellow census and occupancy block with formulas linked to Assumptions.",
        10,
    ),
]
for idx, header in enumerate(ward_headers, start=1):
    ward_cells.append(cell(f"{col_letter(idx)}5", "str", header, 2))

for offset, (name, licensed, staffed, local, share) in enumerate(ward_rows):
    row = 6 + offset
    ward_cells.extend(
        [
            cell(f"A{row}", "str", name, 8),
            cell(f"B{row}", "num", licensed, 8),
            cell(f"C{row}", "num", staffed, 8),
            cell(f"D{row}", "num", local, 8),
            cell(f"E{row}", "num", share, 9),
        ]
    )
    for census_col, occ_col, assumption_col in scenario_cols:
        ward_cells.append(
            cell(
                f"{census_col}{row}",
                "formula",
                ward_values[census_col][offset],
                6,
                f"MIN($C{row},ROUND($D{row}*Assumptions!{assumption_col}$5+$E{row}*Assumptions!{assumption_col}$6,0))",
            )
        )
        ward_cells.append(
            cell(
                f"{occ_col}{row}",
                "formula",
                ward_values[occ_col][offset],
                7,
                f"{census_col}{row}/$C{row}",
            )
        )

summary_metrics = [
    "Total projected census",
    "Available staffed beds",
    "Required RN per shift",
    "Required RT per shift",
    "Required intensivists per day",
    "Effective RN per shift incl. absenteeism",
    "Effective RT per shift incl. absenteeism",
    "Effective intensivists per day incl. absenteeism",
    "Max unit occupancy",
    "Units above 90% occupancy",
]
summary_values = {
    "B": [58, 14, 29, 6, 5, 31, 7, 6, 0.8571428571, 0],
    "C": [70, 2, 40, 9, 6, 44, 10, 7, 1, 4],
    "D": [72, 0, 47, 11, 8, 53, 13, 9, 1, 5],
}
summary_formula_templates = {
    5: "SUM('Ward Load'!{ward_col}6:{ward_col}10)",
    6: "SUM('Ward Load'!$C$6:$C$10)-{scenario_col}5",
    7: "ROUNDUP({scenario_col}5/Assumptions!{assumption_col}$7,0)+Assumptions!{assumption_col}$11",
    8: "ROUNDUP({scenario_col}5/Assumptions!{assumption_col}$8,0)",
    9: "ROUNDUP({scenario_col}5/Assumptions!{assumption_col}$9,0)",
    10: "ROUNDUP({scenario_col}7*(1+Assumptions!{assumption_col}$10),0)",
    11: "ROUNDUP({scenario_col}8*(1+Assumptions!{assumption_col}$10),0)",
    12: "ROUNDUP({scenario_col}9*(1+Assumptions!{assumption_col}$10),0)",
    13: "MAX('Ward Load'!{occ_col}6:{occ_col}10)",
    14: "COUNTIF('Ward Load'!{occ_col}6:{occ_col}10,\">0.9\")",
}

summary_cells = [
    cell("A1", "str", "Staffing Summary by Scenario", 1),
    cell(
        "A3",
        "str",
        "Replace the yellow summary area with formulas only. Keep the scenario columns synchronized.",
        10,
    ),
    cell("A4", "str", "Metric", 2),
    cell("B4", "str", "Baseline", 2),
    cell("C4", "str", "Transfer Surge", 2),
    cell("D4", "str", "Flu Crisis", 2),
]
for row, metric in enumerate(summary_metrics, start=5):
    summary_cells.append(cell(f"A{row}", "str", metric, 3))

for scenario_col, ward_col, occ_col, assumption_col in [
    ("B", "F", "I", "B"),
    ("C", "G", "J", "C"),
    ("D", "H", "K", "D"),
]:
    for row in range(5, 15):
        style = 7 if row == 13 else 6
        summary_cells.append(
            cell(
                f"{scenario_col}{row}",
                "formula",
                summary_values[scenario_col][row - 5],
                style,
                summary_formula_templates[row].format(
                    scenario_col=scenario_col,
                    ward_col=ward_col,
                    occ_col=occ_col,
                    assumption_col=assumption_col,
                ),
            )
        )

sheet2_xml = build_sheet(
    ward_cells,
    merges=["A1:K1"],
    col_widths={1: 22, 2: 14, 3: 14, 4: 14, 5: 14, 6: 16, 7: 18, 8: 16, 9: 18, 10: 20, 11: 18},
    dimension="A1:K10",
    freeze=(5, "A6"),
)
sheet3_xml = build_sheet(
    summary_cells,
    merges=["A1:D1"],
    col_widths={1: 42, 2: 18, 3: 18, 4: 18},
    dimension="A1:D14",
    freeze=(4, "A5"),
)

with ZipFile(INPUT_PATH) as source:
    contents = {name: source.read(name) for name in source.namelist()}

contents["xl/worksheets/sheet2.xml"] = sheet2_xml.encode("utf-8")
contents["xl/worksheets/sheet3.xml"] = sheet3_xml.encode("utf-8")

with ZipFile(OUTPUT_PATH, "w", compression=ZIP_DEFLATED) as target:
    for name, data in contents.items():
        target.writestr(name, data)
PY
