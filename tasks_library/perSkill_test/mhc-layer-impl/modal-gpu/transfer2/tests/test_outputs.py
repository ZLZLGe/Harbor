import csv
import json
import re
from pathlib import Path

csv_path = Path('/root/deployment_matrix.csv')
md_path = Path('/root/modal_jobs/transfer2/deployment_plan.md')
json_path = Path('/root/modal_jobs/transfer2/deployment_plan.json')

assert md_path.exists(), f'missing output: {md_path}'
assert json_path.exists(), f'missing output: {json_path}'

expected = []
with csv_path.open('r', encoding='utf-8', newline='') as f:
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

        expected.append(
            {
                'model_name': model_name,
                'gpu_tier': gpu_tier,
                'concurrency': concurrency,
                'modal_command': modal_command,
            }
        )

actual = json.loads(json_path.read_text(encoding='utf-8'))
assert actual == expected, 'deployment_plan.json does not match expected plan'

md = md_path.read_text(encoding='utf-8')
assert '| model_name | gpu_tier | concurrency | modal_command |' in md
assert '| --- | --- | --- | --- |' in md
for row in expected:
    line = f"| {row['model_name']} | {row['gpu_tier']} | {row['concurrency']} | {row['modal_command']} |"
    assert line in md, f'missing markdown row: {line}'
