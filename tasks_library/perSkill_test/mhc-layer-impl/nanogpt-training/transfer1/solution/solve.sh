#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import json


with open('/root/token_shards.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

tokens = []
for shard in data['shards']:
    tokens.extend(shard)

block_size = int(data['block_size'])
batch_size = int(data['batch_size'])
offsets = list(data['offsets'])

used_tokens = set()
batches = []
for offset in offsets:
    x_rows = []
    y_rows = []
    for i in range(batch_size):
        start = (offset + i * block_size) % len(tokens)
        window = [tokens[(start + j) % len(tokens)] for j in range(block_size + 1)]
        x = window[:-1]
        y = window[1:]
        x_rows.append(x)
        y_rows.append(y)
        used_tokens.update(x)
    batches.append({'offset': int(offset), 'x': x_rows, 'y': y_rows})

unique_total = len(set(tokens))
coverage_ratio = round(len(used_tokens) / unique_total, 6) if unique_total else 0.0

out = {
    'scenario': data['scenario'],
    'num_sequences': len(offsets) * batch_size,
    'unique_token_count': unique_total,
    'coverage_ratio': coverage_ratio,
    'batches': batches,
}

with open('/root/transfer1_loader_report.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY
