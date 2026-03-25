#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import csv
from pathlib import Path
mapping = {'sta_lta': ('screening-only', 'high'), 'deep_learning': ('catalog-first-pass', 'medium'), 'template_matching': ('sequence-refinement', 'medium'), 'manual': ('manual-only', 'high')}
rows = []
with Path('/root/data/review_cases.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        policy = mapping[item['preferred_method']]
        rows.append({'case_id': item['case_id'], 'preferred_method': item['preferred_method'], 'auto_use': policy[0], 'manual_review_level': policy[1]})
with Path('/root/transfer3_review_policy.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['case_id', 'preferred_method', 'auto_use', 'manual_review_level'])
    writer.writeheader(); writer.writerows(rows)
PY2
