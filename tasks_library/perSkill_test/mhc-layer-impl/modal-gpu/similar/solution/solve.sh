#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
from pathlib import Path

spec = json.loads(Path('/root/similar_spec.json').read_text(encoding='utf-8'))
template = Path('/root/train_modal.template.py').read_text(encoding='utf-8')

packages_block = ",\n".join(f'    "{pkg}"' for pkg in spec['packages'])
rendered = (
    template
    .replace('__APP_NAME__', spec['app_name'])
    .replace('__PYTHON_VERSION__', spec['python_version'])
    .replace('__PIP_PACKAGES__', packages_block)
    .replace('__GPU_TYPE__', spec['gpu'])
    .replace('__TIMEOUT_SECONDS__', str(spec['timeout_seconds']))
    .replace('__FUNCTION_NAME__', spec['function_name'])
    .replace('__ENTRYPOINT__', spec['entrypoint'])
)

out_dir = Path('/root/modal_jobs/similar')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'train_modal.py').write_text(rendered, encoding='utf-8')

summary = {
    'app_name': spec['app_name'],
    'gpu': spec['gpu'],
    'timeout_seconds': spec['timeout_seconds'],
    'function_name': spec['function_name'],
    'entrypoint': spec['entrypoint'],
    'package_count': len(spec['packages']),
}
(out_dir / 'launch_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
PY
