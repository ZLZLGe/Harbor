#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import csv
import json
import re
from pathlib import Path

rows = []
with Path('/root/deployment_matrix.csv').open('r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        model_name = row['model_name']
        token_budget_m = int(row['token_budget_m'])
        deadline_minutes = int(row['deadline_minutes'])
        priority = row['priority'].strip().lower()

        if token_budget_m >= 800 or deadline_minutes <= 30:
            gpu_tier = 'A100'
        elif token_budget_m >= 300 or deadline_minutes <= 60:
            gpu_tier = 'A10G'
        else:
            gpu_tier = 'T4'

        concurrency = 2 if priority in {'critical', 'high'} else 1
        slug = re.sub(r'[^a-z0-9]+', '_', model_name.lower()).strip('_')
        modal_command = f'modal run deploy_{slug}.py'

        rows.append(
            {
                'model_name': model_name,
                'gpu_tier': gpu_tier,
                'concurrency': concurrency,
                'modal_command': modal_command,
            }
        )

out_dir = Path('/root/modal_jobs/transfer2')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'deployment_plan.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

lines = [
    '| model_name | gpu_tier | concurrency | modal_command |',
    '| --- | --- | --- | --- |',
]
for item in rows:
    lines.append(
        f"| {item['model_name']} | {item['gpu_tier']} | {item['concurrency']} | {item['modal_command']} |"
    )
(out_dir / 'deployment_plan.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
