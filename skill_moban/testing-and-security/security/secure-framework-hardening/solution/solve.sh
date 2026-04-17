#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

CONTROL_ORDER = [
    'auth_enabled',
    'input_validation',
    'csrf_protection',
    'rate_limit',
    'secrets_vault',
]

workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'security_controls.csv'
output_dir = workspace_root / 'output'
output_path = output_dir / 'hardening_plan.csv'
output_dir.mkdir(parents=True, exist_ok=True)


def priority_for(score: int) -> str:
    if score >= 60:
        return 'critical'
    if score >= 40:
        return 'high'
    if score >= 20:
        return 'medium'
    return 'low'


rows = []
with input_path.open('r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        missing = [control for control in CONTROL_ORDER if row.get(control, '') == 'no']
        score = len(missing) * 20
        rows.append(
            {
                'service': row.get('service', ''),
                'risk_score': str(score),
                'priority': priority_for(score),
                'missing_controls': ';'.join(missing) if missing else 'none',
            }
        )

rows.sort(key=lambda item: (-int(item['risk_score']) if item['risk_score'] else 0, item['service']))

with output_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['service', 'risk_score', 'priority', 'missing_controls'])
    writer.writeheader()
    writer.writerows(rows)
PY
