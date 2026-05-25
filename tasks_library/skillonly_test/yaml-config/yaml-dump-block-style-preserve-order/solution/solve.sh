#!/bin/bash
set -euo pipefail

mkdir -p /root/outputs

python3 - <<'PY'
import json
from pathlib import Path

import yaml

input_path = Path('/root/input/deployment_payload.json')
payload = json.loads(input_path.read_text(encoding='utf-8'))

metadata = {
    'scenario_name': payload['fleet_profile']['name'],
    'locale': payload['fleet_profile']['locale'],
    'owner': payload['fleet_profile']['owner'],
    'revision': payload['fleet_profile']['revision'],
    'generated_by': 'yaml-task-builder',
}

services = []
for service_id in payload['service_order']:
    raw = payload['services'][service_id]
    item = {
        'id': service_id,
        'enabled': raw['enabled'],
        'rollout': {
            'strategy': raw['rollout']['strategy'],
            'batches': raw['rollout']['batches'],
        },
        'endpoints': raw['endpoints'],
    }
    services.append(item)

safety_limits = {key: payload['thresholds'][key] for key in payload['threshold_order']}

notifications = []
for entry in payload['notification_templates']:
    notifications.append(
        {
            'channel': entry['channel'],
            'template': entry['template'],
            'recipients': entry['recipients'],
        }
    )

result = {
    'metadata': metadata,
    'services': services,
    'safety_limits': safety_limits,
    'notifications': notifications,
}

output_path = Path('/root/outputs/generated_config.yaml')
with output_path.open('w', encoding='utf-8') as fh:
    yaml.dump(
        result,
        fh,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
PY
