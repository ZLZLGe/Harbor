#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import csv
from pathlib import Path
rows = []
with Path('/root/data/compute_scenarios.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        large = item['dataset_size'] == 'large'
        rows.append({'scenario_id': item['scenario_id'], 'use_gpu': 'yes' if item['gpu_available'] == 'yes' and large else 'no', 'increase_batch_size': 'yes' if large else 'no', 'compile_model': 'yes' if item['torch2_available'] == 'yes' and large else 'no', 'use_asyncio': 'yes' if item['io_bound'] == 'yes' else 'no', 'manual_resampling': 'yes' if item['sample_rate_mismatch'] == 'yes' else 'no', 'primary_bottleneck': 'io' if item['io_bound'] == 'yes' else 'compute'})
with Path('/root/transfer1_throughput_tuning.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['scenario_id', 'use_gpu', 'increase_batch_size', 'compile_model', 'use_asyncio', 'manual_resampling', 'primary_bottleneck'])
    writer.writeheader(); writer.writerows(rows)
PY2
