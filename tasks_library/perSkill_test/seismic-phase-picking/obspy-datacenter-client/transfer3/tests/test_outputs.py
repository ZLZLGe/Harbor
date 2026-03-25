import csv, json
from pathlib import Path
mapping = {
    'response_archive': ('iris_special', 'iris', 'response-format-service', 'special-response-format'),
    'real_time_feed': ('seedlink', 'seedlink', 'real-time-streaming', 'realtime'),
    'synthetic_waveforms': ('syngine', 'syngine', 'synthetic-waveforms', 'modelled-synthetics'),
    'earthworm_server': ('earthworm', 'earthworm', 'custom-wave-server', 'earthworm-source'),
    'neic_edge': ('neic', 'neic', 'cwb-waveforms', 'neic-edge'),
}
items = json.loads(Path('/root/data/specialty_cases.json').read_text(encoding='utf-8'))
expected = []
for item in sorted(items, key=lambda row: row['request_id']):
    decision = mapping[item['scenario_type']]
    expected.append({'request_id': item['request_id'], 'scenario_type': item['scenario_type'], 'strategy_code': decision[0], 'client_target': decision[1], 'service_family': decision[2], 'why': decision[3]})
with Path('/root/transfer3_specialty_services.csv').open(encoding='utf-8', newline='') as handle:
    actual = list(csv.DictReader(handle))
assert actual == expected
