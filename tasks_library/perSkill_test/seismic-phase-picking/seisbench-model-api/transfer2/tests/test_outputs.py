import json
from pathlib import Path
items = json.loads(Path('/root/data/waveform_flags.json').read_text(encoding='utf-8'))
records = []
for item in sorted(items, key=lambda r: r['record_id']):
    records.append({'record_id': item['record_id'], 'manual_normalization': True, 'scale_before_normalization': item['amplitude_scale'] <= 1e-10, 'preserve_multiple_arrivals': True, 'segment_manually': False})
expected = {'record_count': len(records), 'records': records}
actual = json.loads(Path('/root/transfer2_preprocessing_guardrails.json').read_text(encoding='utf-8'))
assert actual == expected
