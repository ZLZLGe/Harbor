#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import json
from pathlib import Path
items = json.loads(Path('/root/data/deployment_cases.json').read_text(encoding='utf-8'))
plans = []
for item in sorted(items, key=lambda r: r['case_id']):
    if item['prior_templates']:
        decision = ('template_matching', 'deep_learning', 'template-available')
    elif item['compute_budget'] == 'low':
        decision = ('sta_lta', 'manual', 'low-compute')
    elif item['network_density'] == 'sparse':
        decision = ('deep_learning', 'manual', 'sparse-network')
    else:
        decision = ('deep_learning', 'sta_lta', 'balanced-default')
    plans.append({'case_id': item['case_id'], 'preferred_method': decision[0], 'secondary_method': decision[1], 'why': decision[2]})
Path('/root/transfer2_deployment_plan.json').write_text(json.dumps({'case_count': len(plans), 'plans': plans}, indent=2) + chr(10), encoding='utf-8')
PY2
