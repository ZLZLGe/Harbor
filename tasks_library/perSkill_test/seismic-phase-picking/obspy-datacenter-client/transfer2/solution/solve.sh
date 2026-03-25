#!/bin/bash
set -euo pipefail
python3 <<'PY2'
import json
from pathlib import Path
campaigns = json.loads(Path('/root/data/campaigns.json').read_text(encoding='utf-8'))
result = []
for item in sorted(campaigns, key=lambda row: row['campaign_id']):
    if item['waveforms_requested'] >= 500:
        decision = ('mass_downloader', 'mass-downloader', 'volume')
    elif item['geographic_scope'] in {'regional', 'multi-region'}:
        decision = ('mass_downloader', 'mass-downloader', 'geography')
    elif item['station_count'] >= 20 and item['need_station_metadata']:
        decision = ('mass_downloader', 'mass-downloader', 'station-bundle')
    else:
        decision = ('direct_fdsn', 'fdsn', 'small-direct')
    result.append({'campaign_id': item['campaign_id'], 'strategy_code': decision[0], 'client_target': decision[1], 'primary_reason': decision[2]})
summary = {'campaign_count': len(result), 'mass_downloader_count': sum(1 for row in result if row['strategy_code'] == 'mass_downloader'), 'direct_fdsn_count': sum(1 for row in result if row['strategy_code'] == 'direct_fdsn')}
Path('/root/transfer2_campaign_strategy.json').write_text(json.dumps({'summary': summary, 'campaigns': result}, indent=2) + chr(10), encoding='utf-8')
PY2
