#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import json
from pathlib import Path
items = json.loads(Path('/root/data/waveform_flags.json').read_text(encoding='utf-8'))
records = []
for item in sorted(items, key=lambda r: r['record_id']):
    records.append({'record_id': item['record_id'], 'manual_normalization': True, 'scale_before_normalization': item['amplitude_scale'] <= 1e-10, 'preserve_multiple_arrivals': True, 'segment_manually': False})
Path('/root/transfer2_preprocessing_guardrails.json').write_text(json.dumps({'record_count': len(records), 'records': records}, indent=2) + chr(10), encoding='utf-8')
PY2
