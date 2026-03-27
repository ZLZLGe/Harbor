#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
from pathlib import Path

in_path = Path('/root/input/errata_candidates.json')
out_path = Path('/root/transfer1_formula_ledger.json')

rows = json.loads(in_path.read_text(encoding='utf-8'))


def normalize(formula: str) -> str:
    text = re.sub(r"\\tag\{[^}]*\}", "", formula)
    text = re.sub(r"[.,]\s*$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text

ledger = []
for row in rows:
    norm = normalize(str(row['formula']))
    typo_fragment = "\\left[a_m + a_m^\\dagger\\right)"
    needs_fix = typo_fragment in norm
    fixed = (
        norm.replace(
            typo_fragment,
            "\\left(a_m + a_m^\\dagger\\right)",
        )
        if needs_fix
        else ""
    )
    ledger.append(
        {
            'formula_id': str(row['formula_id']),
            'normalized_formula': norm,
            'requires_fix': needs_fix,
            'fixed_formula': fixed,
            'reason': 'mismatched bracket pair fixed' if needs_fix else 'no syntax change needed',
        }
    )

out_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
PY
