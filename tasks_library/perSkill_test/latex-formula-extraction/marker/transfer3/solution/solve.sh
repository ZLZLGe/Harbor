#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

in_path = Path('/root/input/formula_qc_cases.json')
out_path = Path('/root/transfer3_formula_qc_report.md')

cases = json.loads(in_path.read_text(encoding='utf-8'))
total = len(cases)
fixes = sum(1 for c in cases if c.get('requires_fix'))

lines = [
    '# Formula QC Summary',
    f'- Total formulas: {total}',
    f'- Requires fixes: {fixes}',
    '',
    '| formula_id | status | note |',
    '| --- | --- | --- |',
]

for case in cases:
    status = 'fix-required' if case.get('requires_fix') else 'ok'
    lines.append(f"| {case['formula_id']} | {status} | {case['note']} |")

out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
