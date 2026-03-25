#!/bin/bash
set -euo pipefail

cat >/tmp/solve_event_quote.py <<'PY'
#!/usr/bin/env python3
import csv
import json
import subprocess
from pathlib import Path

from openpyxl import load_workbook

TEMPLATE_FILE = Path("/root/event_quote_template.xlsx")
CSV_FILE = Path("/root/new_event_request.csv")
OUTPUT_FILE = Path("/root/event_quote_book.xlsx")
RECALC_SCRIPT = Path("/root/.codex/skills/xlsx/recalc.py")
FIELDS = ["活动名称", "来宾人数", "套餐", "特调饮品站", "舞台灯光", "拍照墙"]


def load_request():
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    row["来宾人数"] = int(row["来宾人数"])
    return row


def write_request(ws, row):
    label_to_row = {}
    for idx in range(1, ws.max_row + 1):
        label = ws.cell(row=idx, column=1).value
        if label is not None:
            label_to_row[str(label).strip()] = idx

    for field in FIELDS:
        ws.cell(row=label_to_row[field], column=2).value = row[field]


def recalc_workbook(path):
    result = subprocess.run(
        ["python3", str(RECALC_SCRIPT), str(path), "90"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    if payload.get("status") != "success":
        raise RuntimeError(f"工作簿重算失败: {payload}")


def main():
    request = load_request()
    workbook = load_workbook(TEMPLATE_FILE)
    try:
        write_request(workbook["需求录入"], request)
        workbook.save(OUTPUT_FILE)
    finally:
        workbook.close()

    recalc_workbook(OUTPUT_FILE)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_event_quote.py
