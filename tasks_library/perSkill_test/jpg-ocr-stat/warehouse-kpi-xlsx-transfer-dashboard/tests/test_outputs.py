import csv
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict


WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
OUTPUT_FILE = os.path.join(WORKSPACE_ROOT, "warehouse_kpi_dashboard.xlsx")
EVENTS_FILE = os.path.join(WORKSPACE_ROOT, "data", "picking_events.csv")
SHIFTS_FILE = os.path.join(WORKSPACE_ROOT, "data", "shifts.csv")

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"main": MAIN_NS, "rel": REL_NS, "pkg": PKG_REL_NS}


def col_name(index: int) -> str:
    name = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def parse_ref(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    assert match, f"invalid cell reference: {ref}"
    letters, digits = match.groups()
    col_index = 0
    for char in letters:
        col_index = col_index * 26 + (ord(char) - 64)
    return int(digits), col_index


def read_csv_rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_workbook(path: str) -> tuple[list[str], dict[str, dict[str, object]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in workbook_rels.findall("pkg:Relationship", NS)
        }

        ordered_names: list[str] = []
        sheets: dict[str, dict[str, object]] = {}
        for sheet in workbook_root.findall("main:sheets/main:sheet", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rel_map[rel_id]
            ordered_names.append(name)
            sheets[name] = load_sheet(archive, f"xl/{target}", shared_strings)
        return ordered_names, sheets


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("main:si", NS):
        texts = [node.text or "" for node in item.findall(".//main:t", NS)]
        strings.append("".join(texts))
    return strings


def load_sheet(archive: zipfile.ZipFile, path: str, shared_strings: list[str]) -> dict[str, object]:
    root = ET.fromstring(archive.read(path))
    cells: dict[str, dict[str, str]] = {}
    max_row = 0
    max_col = 0

    for cell in root.findall(".//main:sheetData/main:row/main:c", NS):
        ref = cell.attrib["r"]
        row_index, col_index = parse_ref(ref)
        max_row = max(max_row, row_index)
        max_col = max(max_col, col_index)

        cell_type = cell.attrib.get("t", "")
        formula_node = cell.find("main:f", NS)
        value_node = cell.find("main:v", NS)

        if cell_type == "inlineStr":
            parts = [node.text or "" for node in cell.findall(".//main:is/main:t", NS)]
            value = "".join(parts)
        elif cell_type == "s":
            assert value_node is not None, f"shared string cell missing value: {ref}"
            value = shared_strings[int(value_node.text)]
        else:
            value = value_node.text if value_node is not None and value_node.text is not None else ""

        formula = formula_node.text if formula_node is not None and formula_node.text is not None else ""
        cells[ref] = {"value": value, "formula": formula}

    return {"cells": cells, "max_row": max_row, "max_col": max_col}


def cell(sheet: dict[str, object], ref: str) -> dict[str, str]:
    return sheet["cells"].get(ref, {"value": "", "formula": ""})  # type: ignore[return-value]


def row_values(sheet: dict[str, object], row_index: int, width: int) -> list[str]:
    return [cell(sheet, f"{col_name(col_index)}{row_index}")["value"] for col_index in range(1, width + 1)]


def assert_close(actual: str, expected: float, *, label: str) -> None:
    assert actual != "", f"{label} is blank"
    actual_value = float(actual)
    assert math.isclose(actual_value, expected, rel_tol=1e-9, abs_tol=1e-9), (
        f"{label} mismatch: actual={actual_value}, expected={expected}"
    )


def main() -> None:
    assert os.path.exists(OUTPUT_FILE), "missing /app/workspace/warehouse_kpi_dashboard.xlsx"

    events = read_csv_rows(EVENTS_FILE)
    shifts = read_csv_rows(SHIFTS_FILE)
    events_by_shift: dict[str, list[dict[str, str]]] = defaultdict(list)
    for event in events:
        events_by_shift[event["shift_id"]].append(event)

    ordered_names, sheets = load_workbook(OUTPUT_FILE)
    assert ordered_names == ["raw_events", "shift_summary", "exceptions", "dashboard"], (
        f"unexpected sheet names/order: {ordered_names}"
    )

    raw_sheet = sheets["raw_events"]
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
    assert row_values(raw_sheet, 1, len(raw_header)) == raw_header, "raw_events header mismatch"
    assert raw_sheet["max_col"] == len(raw_header), f"raw_events column count mismatch: {raw_sheet['max_col']}"
    assert raw_sheet["max_row"] == len(events) + 1, f"raw_events row count mismatch: {raw_sheet['max_row']}"

    for row_number, event in enumerate(events, start=2):
        actual_row = row_values(raw_sheet, row_number, len(raw_header))
        expected_row = [event[key] for key in raw_header]
        for index, key in enumerate(raw_header):
            actual_value = actual_row[index]
            expected_value = expected_row[index]
            if key in {"units_picked", "active_seconds"}:
                assert int(float(actual_value)) == int(expected_value), (
                    f"raw_events {key} mismatch at row {row_number}: actual={actual_value}, expected={expected_value}"
                )
            else:
                assert actual_value == expected_value, (
                    f"raw_events {key} mismatch at row {row_number}: actual={actual_value!r}, expected={expected_value!r}"
                )

    summary_sheet = sheets["shift_summary"]
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
    assert row_values(summary_sheet, 1, len(summary_header)) == summary_header, "shift_summary header mismatch"
    assert summary_sheet["max_col"] == len(summary_header), f"shift_summary column count mismatch: {summary_sheet['max_col']}"
    assert summary_sheet["max_row"] == len(shifts) + 1, f"shift_summary row count mismatch: {summary_sheet['max_row']}"

    formula_columns = ["F", "G", "H", "I", "J", "K", "L", "M"]
    for row_number, shift in enumerate(shifts, start=2):
        shift_events = events_by_shift[shift["shift_id"]]
        event_count = len(shift_events)
        units_picked = sum(int(event["units_picked"]) for event in shift_events)
        total_active_seconds = sum(int(event["active_seconds"]) for event in shift_events)
        overdue_count = sum(1 for event in shift_events if event["overdue_flag"] == "Y")
        exception_count = sum(1 for event in shift_events if event["exception_flag"] == "Y")
        avg_secs = 0 if units_picked == 0 else total_active_seconds / units_picked
        overdue_rate = 0 if event_count == 0 else overdue_count / event_count
        exception_rate = 0 if event_count == 0 else exception_count / event_count
        efficiency_gap = avg_secs - int(shift["target_secs_per_unit"])

        assert cell(summary_sheet, f"A{row_number}")["value"] == shift["shift_id"], "shift_summary shift_id mismatch"
        assert cell(summary_sheet, f"B{row_number}")["value"] == shift["shift_date"], "shift_summary shift_date mismatch"
        assert cell(summary_sheet, f"C{row_number}")["value"] == shift["zone"], "shift_summary zone mismatch"
        assert int(float(cell(summary_sheet, f"D{row_number}")["value"])) == int(shift["picker_count"]), "picker_count mismatch"
        assert int(float(cell(summary_sheet, f"E{row_number}")["value"])) == int(shift["target_secs_per_unit"]), "target_secs_per_unit mismatch"

        assert int(float(cell(summary_sheet, f"F{row_number}")["value"])) == event_count, "event_count mismatch"
        assert int(float(cell(summary_sheet, f"G{row_number}")["value"])) == units_picked, "units_picked mismatch"
        assert int(float(cell(summary_sheet, f"H{row_number}")["value"])) == total_active_seconds, "total_active_seconds mismatch"
        assert_close(cell(summary_sheet, f"I{row_number}")["value"], avg_secs, label=f"avg_secs_per_unit row {row_number}")
        assert_close(cell(summary_sheet, f"J{row_number}")["value"], overdue_rate, label=f"overdue_rate row {row_number}")
        assert int(float(cell(summary_sheet, f"K{row_number}")["value"])) == exception_count, "exception_count mismatch"
        assert_close(cell(summary_sheet, f"L{row_number}")["value"], exception_rate, label=f"exception_rate row {row_number}")
        assert_close(cell(summary_sheet, f"M{row_number}")["value"], efficiency_gap, label=f"efficiency_gap row {row_number}")

        for col in formula_columns:
            assert cell(summary_sheet, f"{col}{row_number}")["formula"], f"missing formula in shift_summary!{col}{row_number}"

    exceptions_sheet = sheets["exceptions"]
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
    assert row_values(exceptions_sheet, 1, len(exceptions_header)) == exceptions_header, "exceptions header mismatch"
    assert exceptions_sheet["max_col"] == len(exceptions_header), f"exceptions column count mismatch: {exceptions_sheet['max_col']}"

    expected_exception_rows = []
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
        expected_exception_rows.append(
            [
                event["event_id"],
                event["shift_id"],
                event["picker_id"],
                issue_type,
                event["overdue_flag"],
                event["exception_flag"],
                event["exception_reason"],
                event["units_picked"],
                event["active_seconds"],
            ]
        )

    assert exceptions_sheet["max_row"] == len(expected_exception_rows) + 1, (
        f"exceptions row count mismatch: {exceptions_sheet['max_row']}"
    )
    for row_number, expected_row in enumerate(expected_exception_rows, start=2):
        actual_row = row_values(exceptions_sheet, row_number, len(exceptions_header))
        for index, value in enumerate(expected_row):
            if index >= 7:
                assert int(float(actual_row[index])) == int(value), (
                    f"exceptions numeric mismatch at row {row_number}, col {index + 1}: actual={actual_row[index]}, expected={value}"
                )
            else:
                assert actual_row[index] == value, (
                    f"exceptions mismatch at row {row_number}, col {index + 1}: actual={actual_row[index]!r}, expected={value!r}"
                )

    dashboard_sheet = sheets["dashboard"]
    dashboard_header = ["metric", "value"]
    assert row_values(dashboard_sheet, 1, 2) == dashboard_header, "dashboard header mismatch"
    assert dashboard_sheet["max_col"] == 2, f"dashboard column count mismatch: {dashboard_sheet['max_col']}"
    assert dashboard_sheet["max_row"] == 8, f"dashboard row count mismatch: {dashboard_sheet['max_row']}"

    total_units = sum(int(event["units_picked"]) for event in events)
    total_seconds = sum(int(event["active_seconds"]) for event in events)
    total_events = len(events)
    total_overdue = sum(1 for event in events if event["overdue_flag"] == "Y")
    total_exceptions = sum(1 for event in events if event["exception_flag"] == "Y")
    avg_by_shift = {
        shift["shift_id"]: (
            0
            if not events_by_shift[shift["shift_id"]]
            else sum(int(event["active_seconds"]) for event in events_by_shift[shift["shift_id"]])
            / sum(int(event["units_picked"]) for event in events_by_shift[shift["shift_id"]])
        )
        for shift in shifts
    }
    overdue_by_shift = {
        shift["shift_id"]: (
            0
            if not events_by_shift[shift["shift_id"]]
            else sum(1 for event in events_by_shift[shift["shift_id"]] if event["overdue_flag"] == "Y")
            / len(events_by_shift[shift["shift_id"]])
        )
        for shift in shifts
    }
    shift_order = [shift["shift_id"] for shift in shifts]
    slowest_shift = max(shift_order, key=lambda value: (avg_by_shift[value], -shift_order.index(value)))
    highest_overdue_rate_shift = max(shift_order, key=lambda value: (overdue_by_shift[value], -shift_order.index(value)))

    expected_dashboard = [
        ("total_shifts", ("number", len(shifts))),
        ("total_units", ("number", total_units)),
        ("weighted_avg_secs_per_unit", ("number", total_seconds / total_units)),
        ("overall_overdue_rate", ("number", total_overdue / total_events)),
        ("overall_exception_rate", ("number", total_exceptions / total_events)),
        ("slowest_shift", ("text", slowest_shift)),
        ("highest_overdue_rate_shift", ("text", highest_overdue_rate_shift)),
    ]

    for row_number, (metric, (value_type, expected_value)) in enumerate(expected_dashboard, start=2):
        assert cell(dashboard_sheet, f"A{row_number}")["value"] == metric, f"dashboard metric mismatch at row {row_number}"
        assert cell(dashboard_sheet, f"B{row_number}")["formula"], f"missing formula in dashboard!B{row_number}"
        actual_value = cell(dashboard_sheet, f"B{row_number}")["value"]
        if value_type == "number":
            assert_close(actual_value, float(expected_value), label=f"dashboard {metric}")
        else:
            assert actual_value == expected_value, (
                f"dashboard {metric} mismatch: actual={actual_value!r}, expected={expected_value!r}"
            )

    print("All checks passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"TEST FAILURE: {exc}", file=sys.stderr)
        raise
