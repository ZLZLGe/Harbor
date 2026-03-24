#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import csv
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_PATH = WORKSPACE / "warehouse_kpi_dashboard.xlsx"
EVENTS_PATH = WORKSPACE / "data" / "picking_events.csv"
SHIFTS_PATH = WORKSPACE / "data" / "shifts.csv"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def text_cell(value: str) -> dict[str, str]:
    return {"kind": "text", "value": value}


def number_cell(value: int | float) -> dict[str, str]:
    return {"kind": "number", "value": format_number(value)}


def formula_number_cell(formula: str, cached_value: int | float) -> dict[str, str]:
    return {"kind": "formula_number", "formula": formula, "value": format_number(cached_value)}


def formula_text_cell(formula: str, cached_value: str) -> dict[str, str]:
    return {"kind": "formula_text", "formula": formula, "value": cached_value}


def format_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.15g}"


def column_name(index: int) -> str:
    name = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def render_cell(reference: str, cell: dict[str, str]) -> str:
    kind = cell["kind"]
    if kind == "text":
        return f'<c r="{reference}" t="inlineStr"><is><t>{escape(cell["value"])}</t></is></c>'
    if kind == "number":
        return f'<c r="{reference}"><v>{cell["value"]}</v></c>'
    if kind == "formula_number":
        return f'<c r="{reference}"><f>{escape(cell["formula"])}</f><v>{cell["value"]}</v></c>'
    if kind == "formula_text":
        return f'<c r="{reference}" t="str"><f>{escape(cell["formula"])}</f><v>{escape(cell["value"])}</v></c>'
    raise ValueError(f"unsupported cell kind: {kind}")


def worksheet_xml(rows: list[list[dict[str, str]]]) -> str:
    max_columns = max((len(row) for row in rows), default=1)
    last_ref = f"{column_name(max_columns)}{len(rows) if rows else 1}"
    rendered_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        rendered_cells = [
            render_cell(f"{column_name(col_index)}{row_index}", cell)
            for col_index, cell in enumerate(row, start=1)
        ]
        rendered_rows.append(f'<row r="{row_index}">{"".join(rendered_cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_ref}"/>'
        f'<sheetData>{"".join(rendered_rows)}</sheetData>'
        '</worksheet>'
    )


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for index, name in enumerate(sheet_names, start=1):
        sheets.append(
            f'<sheet name="{escape(name)}" sheetId="{index}" '
            f'r:id="rId{index}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheets)}</sheets>'
        '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
        '</workbook>'
    )


def workbook_rels_xml(sheet_names: list[str]) -> str:
    relationships = []
    for index, _ in enumerate(sheet_names, start=1):
        relationships.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    relationships.append(
        '<Relationship Id="rId100" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(relationships)}'
        '</Relationships>'
    )


def content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}'
        '</Types>'
    )


def root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def app_xml(sheet_names: list[str]) -> str:
    titles = "".join(f"<vt:lpstr>{escape(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Codex</Application>'
        f'<HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>'
        f'<vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant></vt:vector></HeadingPairs>'
        f'<TitlesOfParts><vt:vector size="{len(sheet_names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>'
        '</Properties>'
    )


def core_xml() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>OpenAI Codex</dc:creator>'
        '<cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def write_xlsx(path: Path, sheets: list[tuple[str, list[list[dict[str, str]]]]]) -> None:
    sheet_names = [name for name, _ in sheets]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("docProps/app.xml", app_xml(sheet_names))
        archive.writestr("docProps/core.xml", core_xml())
        archive.writestr("xl/workbook.xml", workbook_xml(sheet_names))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(sheet_names))
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(rows))


events = read_csv_rows(EVENTS_PATH)
shifts = read_csv_rows(SHIFTS_PATH)
events_by_shift: dict[str, list[dict[str, str]]] = defaultdict(list)
for event in events:
    events_by_shift[event["shift_id"]].append(event)

raw_header = [
    "event_id",
    "shift_id",
    "picker_id",
    "item_sku",
    "units_picked",
    "active_seconds",
    "scan_started_at",
    "scan_finished_at",
    "overdue_flag",
    "exception_flag",
    "exception_reason",
]

raw_rows: list[list[dict[str, str]]] = [[text_cell(value) for value in raw_header]]
for event in events:
    row: list[dict[str, str]] = []
    for field in raw_header:
        if field in {"units_picked", "active_seconds"}:
            row.append(number_cell(int(event[field])))
        else:
            row.append(text_cell(event[field]))
    raw_rows.append(row)

raw_last_row = len(raw_rows)
raw_shift_range = f"raw_events!$B$2:$B${raw_last_row}"
raw_units_range = f"raw_events!$E$2:$E${raw_last_row}"
raw_seconds_range = f"raw_events!$F$2:$F${raw_last_row}"
raw_overdue_range = f"raw_events!$I$2:$I${raw_last_row}"
raw_exception_range = f"raw_events!$J$2:$J${raw_last_row}"

summary_header = [
    "shift_id",
    "shift_date",
    "zone",
    "picker_count",
    "target_secs_per_unit",
    "event_count",
    "units_picked",
    "total_active_seconds",
    "avg_secs_per_unit",
    "overdue_rate",
    "exception_count",
    "exception_rate",
    "efficiency_gap",
]

summary_rows: list[list[dict[str, str]]] = [[text_cell(value) for value in summary_header]]
for excel_row, shift in enumerate(shifts, start=2):
    shift_id = shift["shift_id"]
    shift_events = events_by_shift[shift_id]
    event_count = len(shift_events)
    units_picked = sum(int(event["units_picked"]) for event in shift_events)
    total_active_seconds = sum(int(event["active_seconds"]) for event in shift_events)
    overdue_count = sum(1 for event in shift_events if event["overdue_flag"] == "Y")
    exception_count = sum(1 for event in shift_events if event["exception_flag"] == "Y")
    avg_secs_per_unit = 0 if units_picked == 0 else total_active_seconds / units_picked
    overdue_rate = 0 if event_count == 0 else overdue_count / event_count
    exception_rate = 0 if event_count == 0 else exception_count / event_count
    efficiency_gap = avg_secs_per_unit - int(shift["target_secs_per_unit"])

    summary_rows.append(
        [
            text_cell(shift_id),
            text_cell(shift["shift_date"]),
            text_cell(shift["zone"]),
            number_cell(int(shift["picker_count"])),
            number_cell(int(shift["target_secs_per_unit"])),
            formula_number_cell(f'COUNTIF({raw_shift_range},A{excel_row})', event_count),
            formula_number_cell(f'SUMIF({raw_shift_range},A{excel_row},{raw_units_range})', units_picked),
            formula_number_cell(f'SUMIF({raw_shift_range},A{excel_row},{raw_seconds_range})', total_active_seconds),
            formula_number_cell(f'IF(G{excel_row}=0,0,H{excel_row}/G{excel_row})', avg_secs_per_unit),
            formula_number_cell(
                f'IF(F{excel_row}=0,0,COUNTIFS({raw_shift_range},A{excel_row},{raw_overdue_range},"Y")/F{excel_row})',
                overdue_rate,
            ),
            formula_number_cell(
                f'COUNTIFS({raw_shift_range},A{excel_row},{raw_exception_range},"Y")',
                exception_count,
            ),
            formula_number_cell(f'IF(F{excel_row}=0,0,K{excel_row}/F{excel_row})', exception_rate),
            formula_number_cell(f'I{excel_row}-E{excel_row}', efficiency_gap),
        ]
    )

exceptions_header = [
    "event_id",
    "shift_id",
    "picker_id",
    "issue_type",
    "overdue_flag",
    "exception_flag",
    "exception_reason",
    "units_picked",
    "active_seconds",
]

exception_rows: list[list[dict[str, str]]] = [[text_cell(value) for value in exceptions_header]]
for event in events:
    overdue = event["overdue_flag"] == "Y"
    exception = event["exception_flag"] == "Y"
    if not overdue and not exception:
        continue
    if overdue and exception:
        issue_type = "overdue+exception"
    elif overdue:
        issue_type = "overdue"
    else:
        issue_type = "exception"
    exception_rows.append(
        [
            text_cell(event["event_id"]),
            text_cell(event["shift_id"]),
            text_cell(event["picker_id"]),
            text_cell(issue_type),
            text_cell(event["overdue_flag"]),
            text_cell(event["exception_flag"]),
            text_cell(event["exception_reason"]),
            number_cell(int(event["units_picked"])),
            number_cell(int(event["active_seconds"])),
        ]
    )

summary_last_row = len(summary_rows)
dashboard_header = [text_cell("metric"), text_cell("value")]

shift_ids = [shift["shift_id"] for shift in shifts]
summary_id_range = f"shift_summary!$A$2:$A${summary_last_row}"
summary_event_count_range = f"shift_summary!$F$2:$F${summary_last_row}"
summary_units_range = f"shift_summary!$G$2:$G${summary_last_row}"
summary_seconds_range = f"shift_summary!$H$2:$H${summary_last_row}"
summary_avg_range = f"shift_summary!$I$2:$I${summary_last_row}"
summary_overdue_rate_range = f"shift_summary!$J$2:$J${summary_last_row}"
summary_exception_count_range = f"shift_summary!$K$2:$K${summary_last_row}"

total_shifts = len(shifts)
total_units = sum(int(event["units_picked"]) for event in events)
total_seconds = sum(int(event["active_seconds"]) for event in events)
total_events = len(events)
total_overdue = sum(1 for event in events if event["overdue_flag"] == "Y")
total_exceptions = sum(1 for event in events if event["exception_flag"] == "Y")
weighted_avg_secs = 0 if total_units == 0 else total_seconds / total_units
overall_overdue_rate = 0 if total_events == 0 else total_overdue / total_events
overall_exception_rate = 0 if total_events == 0 else total_exceptions / total_events

avg_by_shift = {
    shift["shift_id"]: (
        0
        if not events_by_shift[shift["shift_id"]]
        else sum(int(event["active_seconds"]) for event in events_by_shift[shift["shift_id"]])
        / sum(int(event["units_picked"]) for event in events_by_shift[shift["shift_id"]])
    )
    for shift in shifts
}
overdue_rate_by_shift = {
    shift["shift_id"]: (
        0
        if not events_by_shift[shift["shift_id"]]
        else sum(1 for event in events_by_shift[shift["shift_id"]] if event["overdue_flag"] == "Y")
        / len(events_by_shift[shift["shift_id"]])
    )
    for shift in shifts
}

slowest_shift = max(shift_ids, key=lambda value: (avg_by_shift[value], -shift_ids.index(value)))
highest_overdue_rate_shift = max(shift_ids, key=lambda value: (overdue_rate_by_shift[value], -shift_ids.index(value)))

dashboard_rows: list[list[dict[str, str]]] = [dashboard_header]
dashboard_specs = [
    ("total_shifts", f'COUNTA({summary_id_range})', total_shifts, "number"),
    ("total_units", f'SUM({summary_units_range})', total_units, "number"),
    ("weighted_avg_secs_per_unit", f'IF(B3=0,0,SUM({summary_seconds_range})/B3)', weighted_avg_secs, "number"),
    (
        "overall_overdue_rate",
        f'IF(SUM({summary_event_count_range})=0,0,SUMPRODUCT({summary_event_count_range},{summary_overdue_rate_range})/SUM({summary_event_count_range}))',
        overall_overdue_rate,
        "number",
    ),
    (
        "overall_exception_rate",
        f'IF(SUM({summary_event_count_range})=0,0,SUM({summary_exception_count_range})/SUM({summary_event_count_range}))',
        overall_exception_rate,
        "number",
    ),
    (
        "slowest_shift",
        f'INDEX({summary_id_range},MATCH(MAX({summary_avg_range}),{summary_avg_range},0))',
        slowest_shift,
        "text",
    ),
    (
        "highest_overdue_rate_shift",
        f'INDEX({summary_id_range},MATCH(MAX({summary_overdue_rate_range}),{summary_overdue_rate_range},0))',
        highest_overdue_rate_shift,
        "text",
    ),
]

for metric, formula, cached, value_type in dashboard_specs:
    if value_type == "number":
        value_cell = formula_number_cell(formula, cached)
    else:
        value_cell = formula_text_cell(formula, str(cached))
    dashboard_rows.append([text_cell(metric), value_cell])

write_xlsx(
    OUTPUT_PATH,
    [
        ("raw_events", raw_rows),
        ("shift_summary", summary_rows),
        ("exceptions", exception_rows),
        ("dashboard", dashboard_rows),
    ],
)
PY
