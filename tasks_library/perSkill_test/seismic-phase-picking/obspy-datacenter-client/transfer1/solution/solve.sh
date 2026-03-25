#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import csv
from pathlib import Path
rows = []
with Path('/root/data/routing_requests.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        if item['datacenter_hint'].strip():
            rows.append({'request_id': item['request_id'], 'strategy_code': 'direct_fdsn', 'routing_service': 'none', 'client_target': 'fdsn', 'why': 'known-provider'})
        elif item['region_code'] == 'EU':
            rows.append({'request_id': item['request_id'], 'strategy_code': 'route_then_fdsn', 'routing_service': 'eidaws-routing', 'client_target': 'fdsn', 'why': 'unknown-provider-eu'})
        else:
            rows.append({'request_id': item['request_id'], 'strategy_code': 'route_then_fdsn', 'routing_service': 'iris-federator', 'client_target': 'fdsn', 'why': 'unknown-provider-global'})
with Path('/root/transfer1_routing_matrix.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['request_id', 'strategy_code', 'routing_service', 'client_target', 'why'])
    writer.writeheader(); writer.writerows(rows)
PY2
