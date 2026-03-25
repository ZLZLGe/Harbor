#!/bin/bash
set -euo pipefail

cat >/tmp/solve_fx_matrix.py <<'PY'
#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

from openpyxl import load_workbook

INPUT_FILE = Path("/root/fx_matrix.xlsx")
OUTPUT_FILE = Path("/root/fx_matrix_updated.xlsx")
RECALC_SCRIPT = Path("/root/.codex/skills/xlsx/recalc.py")


def is_formula(value):
    return isinstance(value, str) and value.startswith("=")


def load_pending_update(notes_ws):
    header = {}
    for col in range(1, notes_ws.max_column + 1):
        value = notes_ws.cell(row=1, column=col).value
        if value:
            header[str(value).strip()] = col

    for row in range(2, notes_ws.max_row + 1):
        status = notes_ws.cell(row=row, column=header["状态"]).value
        if str(status).strip() != "待执行":
            continue

        pair = str(notes_ws.cell(row=row, column=header["货币对"]).value).strip()
        rate = float(notes_ws.cell(row=row, column=header["新汇率"]).value)
        base, quote = [part.strip().upper() for part in pair.split("/", 1)]
        return base, quote, rate

    raise ValueError("未找到状态为待执行的备注记录")


def build_matrix_maps(matrix_ws):
    col_map = {}
    for col in range(2, matrix_ws.max_column + 1):
        value = matrix_ws.cell(row=1, column=col).value
        if value:
            col_map[str(value).strip().upper()] = col

    row_map = {}
    for row in range(2, matrix_ws.max_row + 1):
        value = matrix_ws.cell(row=row, column=1).value
        if value:
            row_map[str(value).strip().upper()] = row

    return row_map, col_map


def update_matrix(matrix_ws, base, quote, target_rate):
    row_map, col_map = build_matrix_maps(matrix_ws)
    direct_cell = matrix_ws.cell(row=row_map[base], column=col_map[quote])

    if is_formula(direct_cell.value):
        inverse_cell = matrix_ws.cell(row=row_map[quote], column=col_map[base])
        if is_formula(inverse_cell.value):
            raise ValueError(f"{base}/{quote} 两个方向都不是可编辑输入单元格")
        inverse_cell.value = 1 / target_rate
    else:
        direct_cell.value = target_rate


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
        raise RuntimeError(f"重算后存在公式错误: {payload}")


def main():
    wb = load_workbook(INPUT_FILE)
    matrix_ws = wb["汇率矩阵"]
    notes_ws = wb["更新备注"]

    base, quote, target_rate = load_pending_update(notes_ws)
    update_matrix(matrix_ws, base, quote, target_rate)

    wb.save(OUTPUT_FILE)
    wb.close()
    recalc_workbook(OUTPUT_FILE)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_fx_matrix.py
