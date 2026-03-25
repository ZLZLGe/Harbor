#!/bin/bash
set -euo pipefail

cat > /tmp/solve_close_tracker.py <<'PY'
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

INPUT_FILE = Path("/root/close_tracker_template.xlsx")
OUTPUT_FILE = Path("/root/close_tracker_repaired.xlsx")

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def set_tracker_formulas(ws) -> None:
    for row in range(4, 9):
        ws[f"G{row}"] = f'=IF(F{row}="","Open",IF(F{row}<=E{row},"On Time","Late"))'
        ws[f"H{row}"] = f'=IF(F{row}="","",MAX(F{row}-E{row},0))'
        ws[f"I{row}"] = (
            f'=INDEX(\'Owner Map\'!$C$2:$C$5,MATCH(C{row},\'Owner Map\'!$A$2:$A$5,0))'
        )
        ws[f"J{row}"] = f'=IF(AND(G{row}="Late",H{row}>=2),"Escalate","")'


def set_dashboard_formulas(ws) -> None:
    ws["B2"] = "=COUNTA('Close Tracker'!A4:A8)"
    ws["B3"] = '=COUNTIF(\'Close Tracker\'!G4:G8,"Late")'
    ws["B4"] = '=COUNTIF(\'Close Tracker\'!G4:G8,"On Time")'
    ws["B5"] = '=COUNTIF(\'Close Tracker\'!G4:G8,"Open")'
    ws["B6"] = '=COUNTIF(\'Close Tracker\'!J4:J8,"Escalate")'
    ws["B7"] = "=MAX('Close Tracker'!H4:H8)"
    ws["B8"] = '=AVERAGEIF(\'Close Tracker\'!H4:H8,">0")'


def build_cached_values(workbook) -> dict[str, dict[str, tuple[str | None, str]]]:
    tracker = workbook["Close Tracker"]
    owner_map = workbook["Owner Map"]

    owner_emails = {
        owner_map[f"A{row}"].value: owner_map[f"C{row}"].value
        for row in range(3, 7)
    }

    tracker_cache: dict[str, tuple[str | None, str]] = {}
    status_counts = {"Late": 0, "On Time": 0, "Open": 0}
    escalation_count = 0
    max_delay = 0
    positive_delays: list[int] = []
    tracked_items = 0

    for row in range(4, 9):
        owner_id = tracker[f"C{row}"].value
        planned_day = tracker[f"E{row}"].value
        actual_day = tracker[f"F{row}"].value

        tracked_items += 1

        if actual_day in ("", None):
            status = "Open"
            delay_value = ""
            delay_days = None
        else:
            delay_days = max(actual_day - planned_day, 0)
            delay_value = str(delay_days)
            status = "On Time" if actual_day <= planned_day else "Late"
            max_delay = max(max_delay, delay_days)
            if delay_days > 0:
                positive_delays.append(delay_days)

        escalation = "Escalate" if status == "Late" and (delay_days or 0) >= 2 else ""
        owner_email = owner_emails[owner_id]

        status_counts[status] += 1
        if escalation:
            escalation_count += 1

        tracker_cache[f"G{row}"] = ("str", status)
        tracker_cache[f"H{row}"] = ("str", "") if delay_days is None else (None, delay_value)
        tracker_cache[f"I{row}"] = ("str", owner_email)
        tracker_cache[f"J{row}"] = ("str", escalation)

    average_delay = sum(positive_delays) / len(positive_delays) if positive_delays else 0
    dashboard_cache = {
        "B2": (None, str(tracked_items)),
        "B3": (None, str(status_counts["Late"])),
        "B4": (None, str(status_counts["On Time"])),
        "B5": (None, str(status_counts["Open"])),
        "B6": (None, str(escalation_count)),
        "B7": (None, str(max_delay)),
        "B8": (None, f"{average_delay:g}"),
    }

    return {
        "xl/worksheets/sheet1.xml": tracker_cache,
        "xl/worksheets/sheet3.xml": dashboard_cache,
    }


def cache_formula_results(path: Path, workbook) -> None:
    cached_values = build_cached_values(workbook)

    temp_path = path.with_suffix(".tmp.xlsx")
    ET.register_namespace("", NS)

    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
        temp_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename in cached_values:
                tree = ET.fromstring(data)
                for cell_ref, (cell_type, value) in cached_values[item.filename].items():
                    cell = tree.find(f".//{{{NS}}}c[@r='{cell_ref}']")
                    if cell is None:
                        continue
                    if cell_type is None:
                        cell.attrib.pop("t", None)
                    else:
                        cell.attrib["t"] = cell_type
                    value_node = cell.find(f"{{{NS}}}v")
                    if value_node is None:
                        value_node = ET.SubElement(cell, f"{{{NS}}}v")
                    value_node.text = value
                data = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
            target.writestr(item, data)

    shutil.move(temp_path, path)


def main() -> None:
    workbook = load_workbook(INPUT_FILE)
    set_tracker_formulas(workbook["Close Tracker"])
    set_dashboard_formulas(workbook["Dashboard"])
    workbook.save(OUTPUT_FILE)
    cache_formula_results(OUTPUT_FILE, workbook)
    workbook.close()


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_close_tracker.py
