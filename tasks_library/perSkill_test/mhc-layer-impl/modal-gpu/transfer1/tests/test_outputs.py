import json
from pathlib import Path

jobs = json.loads(Path('/root/transfer1_jobs.json').read_text(encoding='utf-8'))
script_path = Path('/root/modal_jobs/transfer1/batch_jobs.py')
manifest_path = Path('/root/modal_jobs/transfer1/results_manifest.json')

assert script_path.exists(), f'missing output: {script_path}'
assert manifest_path.exists(), f'missing output: {manifest_path}'

content = script_path.read_text(encoding='utf-8')
assert '__' not in content, 'placeholder token still present in batch_jobs.py'
assert 'import modal' in content
assert 'app = modal.App("mhc-transfer-batch")' in content
assert '@app.local_entrypoint()' in content

for job in jobs:
    func_name = f"run_{job['job_id'].replace('-', '_')}"
    assert f'def {func_name}(' in content, f'missing function {func_name}'
    assert f'gpu="{job["gpu"]}"' in content, f'missing gpu for {job["job_id"]}'
    assert f'timeout={job["timeout_seconds"]}' in content, f'missing timeout for {job["job_id"]}'
    assert f'{func_name}.remote()' in content, f'missing remote call for {func_name}'

manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
expected = []
for job in jobs:
    expected.append(
        {
            'job_id': job['job_id'],
            'function_name': f"run_{job['job_id'].replace('-', '_')}",
            'gpu': job['gpu'],
            'timeout_minutes': job['timeout_seconds'] // 60,
        }
    )
expected = sorted(expected, key=lambda row: row['job_id'])
assert manifest == expected, 'results_manifest.json does not match expected rows'
