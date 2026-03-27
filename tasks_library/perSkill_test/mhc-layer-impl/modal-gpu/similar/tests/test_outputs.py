import json
from pathlib import Path

spec = json.loads(Path('/root/similar_spec.json').read_text(encoding='utf-8'))
script_path = Path('/root/modal_jobs/similar/train_modal.py')
summary_path = Path('/root/modal_jobs/similar/launch_summary.json')

assert script_path.exists(), f'missing output: {script_path}'
assert summary_path.exists(), f'missing output: {summary_path}'

content = script_path.read_text(encoding='utf-8')
assert '__' not in content, 'placeholder token still present in train_modal.py'

assert 'import modal' in content
assert f'app = modal.App("{spec["app_name"]}")' in content
assert 'modal.Image.debian_slim' in content
assert f'python_version="{spec["python_version"]}"' in content
assert f'gpu="{spec["gpu"]}"' in content
assert f'timeout={spec["timeout_seconds"]}' in content
assert f'def {spec["function_name"]}(' in content
assert '@app.local_entrypoint()' in content
assert f'{spec["function_name"]}.remote()' in content

for pkg in spec['packages']:
    assert (f'"{pkg}"' in content) or (f"'{pkg}'" in content), f'missing package {pkg}'

summary = json.loads(summary_path.read_text(encoding='utf-8'))
assert set(summary.keys()) == {
    'app_name',
    'gpu',
    'timeout_seconds',
    'function_name',
    'entrypoint',
    'package_count',
}
assert summary['app_name'] == spec['app_name']
assert summary['gpu'] == spec['gpu']
assert summary['timeout_seconds'] == spec['timeout_seconds']
assert summary['function_name'] == spec['function_name']
assert summary['entrypoint'] == spec['entrypoint']
assert summary['package_count'] == len(spec['packages'])
