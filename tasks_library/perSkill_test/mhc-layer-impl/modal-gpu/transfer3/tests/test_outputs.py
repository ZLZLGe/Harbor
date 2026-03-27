import json
from pathlib import Path

input_path = Path('/root/failure_events.json')
json_path = Path('/root/modal_jobs/transfer3/recovery_playbook.json')
script_path = Path('/root/modal_jobs/transfer3/retry_modal.py')

assert json_path.exists(), f'missing output: {json_path}'
assert script_path.exists(), f'missing output: {script_path}'


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


events = json.loads(input_path.read_text(encoding='utf-8'))
expected = []
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

    expected.append(
        {
            'run_id': event['run_id'],
            'next_attempt': int(event['attempts']) + 1,
            'recommended_gpu': rec_gpu,
            'action': action,
            'retry_delay_seconds': delay,
        }
    )

actual = json.loads(json_path.read_text(encoding='utf-8'))
assert actual == expected, 'recovery_playbook.json does not match expected rows'

content = script_path.read_text(encoding='utf-8')
assert 'import modal' in content
assert 'app = modal.App("mhc-transfer-recovery")' in content
assert 'def select_retry_config(event):' in content
assert '@app.function(' in content
for token in ['timeout', 'oom', 'network', 'quota', 'increase-timeout', 'shrink-batch-upgrade-gpu', 'retry-network', 'offpeak-fallback']:
    assert token in content, f'missing token in retry_modal.py: {token}'
