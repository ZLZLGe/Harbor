#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
from pathlib import Path

in_path = Path('/root/input/formula_candidates.json')
out_path = Path('/root/similar_standalone_formulas.md')

rows = json.loads(in_path.read_text(encoding='utf-8'))


def normalize_formula(formula: str) -> str:
    text = re.sub(r"\\tag\{[^}]*\}", "", formula)
    text = re.sub(r"[.,]\s*$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text

lines = []
for row in rows:
    if not row.get('is_standalone'):
        continue
    cleaned = normalize_formula(str(row['formula']))
    lines.append(f"$${cleaned}$$")

for line in list(lines):
    body = line[2:-2]
    typo_fragment = "\\left[a_m + a_m^\\dagger\\right)"
    if typo_fragment in body:
        fixed_body = body.replace(
            typo_fragment,
            "\\left(a_m + a_m^\\dagger\\right)",
        )
        fixed_line = f"$${fixed_body}$$"
        if fixed_line not in lines:
            lines.append(fixed_line)
        break

out_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
PY
