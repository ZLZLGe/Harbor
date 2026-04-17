#!/bin/bash
set -e

python3 - <<'PY'
import csv
import json
import os
from pathlib import Path

workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'findings.jsonl'
output_dir = workspace_root / 'output'
output_path = output_dir / 'remediation_queue.csv'
output_dir.mkdir(parents=True, exist_ok=True)

severity_rank = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
owner_team_map = {
    'sast': 'appsec',
    'deps': 'appsec',
    'api': 'backend',
    'pentest': 'cloudsec',
}
sla_map = {
    'critical': '3',
    'high': '7',
    'medium': '30',
    'low': '90',
}
fieldnames = ['finding_key', 'severity', 'scanner', 'owner_team', 'sla_days', 'fix_version']

best_by_key = {}
with input_path.open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        scanner = str(record.get('scanner') or '').strip()
        finding_id = str(record.get('id') or '').strip()
        severity = str(record.get('severity') or '').strip().lower()
        cve_raw = record.get('cve')
        cve = '' if cve_raw is None else str(cve_raw).strip()
        fix_raw = record.get('fix_version')
        fix_version = '' if fix_raw is None else str(fix_raw).strip()
        finding_key = cve if cve else finding_id

        candidate = {
            'finding_key': finding_key,
            'severity': severity,
            'scanner': scanner,
            'owner_team': owner_team_map.get(scanner, 'platform'),
            'sla_days': sla_map[severity],
            'fix_version': fix_version,
        }

        current = best_by_key.get(finding_key)
        if current is None:
            best_by_key[finding_key] = candidate
            continue

        current_rank = severity_rank[current['severity']]
        candidate_rank = severity_rank[severity]
        if candidate_rank > current_rank:
            best_by_key[finding_key] = candidate
        elif candidate_rank == current_rank and scanner < current['scanner']:
            best_by_key[finding_key] = candidate

rows = list(best_by_key.values())
rows.sort(key=lambda row: (-severity_rank[row['severity']], row['finding_key']))

with output_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
PY
