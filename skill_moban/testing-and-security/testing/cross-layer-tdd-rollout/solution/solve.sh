#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

OUTPUT_FIELDS = [
    'feature_id',
    'user_journey',
    'unit_focus',
    'integration_focus',
    'e2e_focus',
    'coverage_gate',
    'checkpoint_plan',
]
CHECKPOINT_PLAN = 'journey-tests -> unit-red-green -> integration-red-green -> e2e-error-path -> coverage-gate'
COVERAGE_GATES = {
    'critical': 'unit>=95%;integration>=90%;e2e=required',
    'high': 'unit>=90%;integration>=80%;e2e=required',
    'medium': 'unit>=85%;integration>=70%;e2e=targeted',
    'low': 'unit>=80%;integration>=60%;e2e=smoke',
}


def user_journey(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return f"{row['user_role']} journey -> UI to API before code"
    if row['has_ui'] == 'yes':
        return f"{row['user_role']} journey -> UI interaction before code"
    if row['has_api'] == 'yes':
        return f"{row['user_role']} journey -> API flow before code"
    return f"{row['user_role']} journey -> offline workflow before code"


def unit_focus(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return 'domain rules;UI state;API adapters;error paths'
    if row['has_ui'] == 'yes':
        return 'domain rules;UI state;error paths'
    if row['has_api'] == 'yes':
        return 'domain rules;API handlers;error paths'
    return 'domain rules;pure functions;error paths'


def integration_focus(row: dict[str, str]) -> str:
    if row['has_external_service'] == 'yes' and row['has_api'] == 'yes':
        return 'API contracts;persistence;external failure path'
    if row['has_external_service'] == 'yes':
        return 'module seams;external failure path'
    if row['has_api'] == 'yes':
        return 'API contracts;persistence'
    return 'module seams only'


def e2e_focus(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_external_service'] == 'yes':
        return 'happy path;dependency outage'
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return 'happy path;API validation failure'
    if row['has_ui'] == 'yes':
        return 'happy path;client validation failure'
    if row['has_api'] == 'yes':
        return 'consumer smoke;auth failure'
    if row['has_external_service'] == 'yes':
        return 'orchestrator smoke;dependency outage'
    return 'batch smoke;invalid input'


workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'features.csv'
output_dir = workspace_root / 'output'
output_path = output_dir / 'tdd_rollout.csv'
output_dir.mkdir(parents=True, exist_ok=True)

rows = []
with input_path.open('r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(
            {
                'feature_id': row.get('feature_id', ''),
                'user_journey': user_journey(row),
                'unit_focus': unit_focus(row),
                'integration_focus': integration_focus(row),
                'e2e_focus': e2e_focus(row),
                'coverage_gate': COVERAGE_GATES[row.get('risk_level', 'low')],
                'checkpoint_plan': CHECKPOINT_PLAN,
            }
        )

rows.sort(key=lambda item: item['feature_id'])

with output_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
PY
