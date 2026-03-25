#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import csv
from pathlib import Path
mapping = {'tiny-known': ('template_matching', 'deep_learning', 'manual', 'sta_lta'), 'sparse-unknown': ('deep_learning', 'manual', 'sta_lta', 'template_matching'), 'rapid-screen': ('sta_lta', 'deep_learning', 'manual', 'template_matching'), 'quality-audit': ('manual', 'deep_learning', 'template_matching', 'sta_lta')}
rows = []
with Path('/root/data/ranking_cases.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        rank = mapping[item['priority_code']]
        rows.append({'case_id': item['case_id'], 'first_choice': rank[0], 'second_choice': rank[1], 'third_choice': rank[2], 'fourth_choice': rank[3]})
with Path('/root/transfer1_method_ranking.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['case_id', 'first_choice', 'second_choice', 'third_choice', 'fourth_choice'])
    writer.writeheader(); writer.writerows(rows)
PY2
