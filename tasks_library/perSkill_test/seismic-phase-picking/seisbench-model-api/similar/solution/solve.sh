#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import json
from pathlib import Path
items = json.loads(Path('/root/data/phase_scenarios.json').read_text(encoding='utf-8'))
plans = []
for item in sorted(items, key=lambda r: r['scenario_id']):
    plans.append({'scenario_id': item['scenario_id'], 'model_family': 'phasenet', 'api_mode': 'classify', 'pretrained_weights': 'original', 'scale_tiny_waveforms': item['amplitude_scale'] <= 1e-10, 'treat_as_continuous_stream': True})
Path('/root/similar_inference_runbook.json').write_text(json.dumps({'scenario_count': len(plans), 'plans': plans}, indent=2) + chr(10), encoding='utf-8')
PY2
