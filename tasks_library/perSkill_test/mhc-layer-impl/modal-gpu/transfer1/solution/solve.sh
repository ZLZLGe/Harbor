#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
from pathlib import Path

jobs = json.loads(Path('/root/transfer1_jobs.json').read_text(encoding='utf-8'))
template = Path('/root/transfer1_template.py').read_text(encoding='utf-8')

blocks = []
calls = []
manifest = []

for job in jobs:
    func_name = f"run_{job['job_id'].replace('-', '_')}"
    block = f'''@app.function(gpu="{job['gpu']}", image=base_image, timeout={job['timeout_seconds']})
def {func_name}():
    return {{"job_id": "{job['job_id']}", "status": "queued", "gpu": "{job['gpu']}"}}
'''
    blocks.append(block.rstrip())
    calls.append(f"    results.append({func_name}.remote())")
    manifest.append(
        {
            'job_id': job['job_id'],
            'function_name': func_name,
            'gpu': job['gpu'],
            'timeout_minutes': job['timeout_seconds'] // 60,
        }
    )

manifest = sorted(manifest, key=lambda row: row['job_id'])

rendered = (
    template
    .replace('__FUNCTION_BLOCKS__', '\n\n'.join(blocks))
    .replace('__ENTRYPOINT_CALLS__', '\n'.join(calls))
)

out_dir = Path('/root/modal_jobs/transfer1')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'batch_jobs.py').write_text(rendered, encoding='utf-8')
(out_dir / 'results_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
PY
