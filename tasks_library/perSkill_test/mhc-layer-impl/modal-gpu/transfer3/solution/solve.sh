#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
from pathlib import Path


def upgrade_gpu(gpu: str) -> str:
    if gpu == 'T4':
        return 'A10G'
    if gpu == 'A10G':
        return 'A100'
    return 'A100'


def downgrade_gpu(gpu: str) -> str:
    if gpu == 'A100':
        return 'A10G'
    if gpu == 'A10G':
        return 'T4'
    return 'T4'


events = json.loads(Path('/root/failure_events.json').read_text(encoding='utf-8'))
rows = []
for event in events:
    kind = event['error_type']
    gpu = event['gpu']
    if kind == 'timeout':
        rec_gpu = gpu
        action = 'increase-timeout'
        delay = 60
    elif kind == 'oom':
        rec_gpu = upgrade_gpu(gpu)
        action = 'shrink-batch-upgrade-gpu'
        delay = 30
    elif kind == 'network':
        rec_gpu = gpu
        action = 'retry-network'
        delay = 120
    elif kind == 'quota':
        rec_gpu = downgrade_gpu(gpu)
        action = 'offpeak-fallback'
        delay = 300
    else:
        rec_gpu = gpu
        action = 'manual-review'
        delay = 600

    rows.append(
        {
            'run_id': event['run_id'],
            'next_attempt': int(event['attempts']) + 1,
            'recommended_gpu': rec_gpu,
            'action': action,
            'retry_delay_seconds': delay,
        }
    )

out_dir = Path('/root/modal_jobs/transfer3')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'recovery_playbook.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

script = '''import modal

app = modal.App("mhc-transfer-recovery")


def _upgrade_gpu(gpu: str) -> str:
    if gpu == "T4":
        return "A10G"
    if gpu == "A10G":
        return "A100"
    return "A100"


def _downgrade_gpu(gpu: str) -> str:
    if gpu == "A100":
        return "A10G"
    if gpu == "A10G":
        return "T4"
    return "T4"


def select_retry_config(event):
    kind = event["error_type"]
    gpu = event["gpu"]
    if kind == "timeout":
        return {"recommended_gpu": gpu, "action": "increase-timeout", "retry_delay_seconds": 60}
    if kind == "oom":
        return {"recommended_gpu": _upgrade_gpu(gpu), "action": "shrink-batch-upgrade-gpu", "retry_delay_seconds": 30}
    if kind == "network":
        return {"recommended_gpu": gpu, "action": "retry-network", "retry_delay_seconds": 120}
    if kind == "quota":
        return {"recommended_gpu": _downgrade_gpu(gpu), "action": "offpeak-fallback", "retry_delay_seconds": 300}
    return {"recommended_gpu": gpu, "action": "manual-review", "retry_delay_seconds": 600}


@app.function(gpu="T4", timeout=900)
def build_retry_ticket(event):
    cfg = select_retry_config(event)
    return {
        "run_id": event["run_id"],
        "next_attempt": int(event["attempts"]) + 1,
        "recommended_gpu": cfg["recommended_gpu"],
        "action": cfg["action"],
        "retry_delay_seconds": cfg["retry_delay_seconds"],
    }
'''
(out_dir / 'retry_modal.py').write_text(script, encoding='utf-8')
PY
