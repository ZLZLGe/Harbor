#!/bin/bash
set -e

python3 - <<'PY'
import json
import os
from pathlib import Path

workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'platform_controls.json'
output_dir = workspace_root / 'output'
output_path = output_dir / 'control_bundle.json'
output_dir.mkdir(parents=True, exist_ok=True)

with input_path.open('r', encoding='utf-8') as f:
    payload = json.load(f)

allowed_secret_stores = {'vault', '1password', 'keyvault'}
services = []
failed_services = 0

for raw_service in payload.get('services', []):
    name = raw_service.get('name', '')
    namespace = raw_service.get('namespace', '')
    mtls = raw_service.get('mtls')
    secret_store = raw_service.get('secret_store')
    network_policy = raw_service.get('network_policy')
    cert_expiry_days = raw_service.get('cert_expiry_days')

    violations = []
    if mtls != 'required':
        violations.append('mtls_missing')
    if secret_store not in allowed_secret_stores:
        violations.append('weak_secret_store')
    if network_policy != 'strict':
        violations.append('network_open')
    if cert_expiry_days < 15:
        violations.append('cert_rotation_urgent')

    status = 'fail' if violations else 'pass'
    rotation_priority = 'urgent' if cert_expiry_days < 15 else 'normal'
    if status == 'fail':
        failed_services += 1

    services.append(
        {
            'name': name,
            'namespace': namespace,
            'status': status,
            'rotation_priority': rotation_priority,
            'violations': violations,
        }
    )

services.sort(key=lambda item: item['name'])

result = {
    'summary': {
        'total_services': len(services),
        'failed_services': failed_services,
    },
    'services': services,
}

with output_path.open('w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')
PY
