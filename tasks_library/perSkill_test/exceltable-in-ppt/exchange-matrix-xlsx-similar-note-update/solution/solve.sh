#!/bin/bash
set -euo pipefail

cat > /tmp/update_exchange_matrix.py <<'PY'
from pathlib import Path
import subprocess

from openpyxl import load_workbook

INPUT_FILE = Path("/root/input_exchange_matrix.xlsx")
OUTPUT_FILE = Path("/root/results_exchange_matrix.xlsx")
RECALC_SCRIPT = Path("/root/.codex/skills/xlsx/recalc.py")


def is_formula(cell):
    return isinstance(cell.value, str) and cell.value.startswith("=")


wb = load_workbook(INPUT_FILE)
matrix = wb["汇率矩阵"]
note = wb["更新说明"]

base_currency = str(note["B4"].value).strip()
quote_currency = str(note["B5"].value).strip()
new_rate = float(note["B6"].value)

row_map = {}
for row_idx in range(2, matrix.max_row + 1):
    value = matrix.cell(row=row_idx, column=1).value
    if value is None:
        continue
    row_map[str(value).strip()] = row_idx

col_map = {}
for col_idx in range(2, matrix.max_column + 1):
    value = matrix.cell(row=1, column=col_idx).value
    if value is None:
        continue
    col_map[str(value).strip()] = col_idx

direct_cell = matrix.cell(row=row_map[base_currency], column=col_map[quote_currency])
inverse_cell = matrix.cell(row=row_map[quote_currency], column=col_map[base_currency])

if is_formula(direct_cell) and not is_formula(inverse_cell):
    inverse_cell.value = 1 / new_rate
elif not is_formula(direct_cell):
    direct_cell.value = new_rate
else:
    raise RuntimeError(f"Could not find a single editable value cell for {base_currency} -> {quote_currency}")

wb.save(OUTPUT_FILE)

result = subprocess.run(
    ["python3", str(RECALC_SCRIPT), str(OUTPUT_FILE), "60"],
    check=False,
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.returncode != 0:
    raise SystemExit(result.stderr or f"Recalc failed with exit code {result.returncode}")
PY

python3 /tmp/update_exchange_matrix.py
