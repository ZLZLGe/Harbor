import json
from pathlib import Path
items = json.loads(Path('/root/data/picker_scenarios.json').read_text(encoding='utf-8'))
out = []
for item in sorted(items, key=lambda r: r['scenario_id']):
    if item['prior_templates'] and item['target_signal'] == 'small':
        decision = ('template_matching', 'template-sensitive', False)
    elif item['network_density'] == 'sparse':
        decision = ('deep_learning', 'sparse-network', False)
    elif item['urgency'] == 'realtime':
        decision = ('sta_lta', 'realtime-large-signal', True)
    else:
        decision = ('deep_learning', 'balanced-catalog', False)
    out.append({'scenario_id': item['scenario_id'], 'recommended_method': decision[0], 'reason_code': decision[1], 'needs_manual_review': decision[2]})
expected = {'scenario_count': len(out), 'recommendations': out}
actual = json.loads(Path('/root/similar_picker_brief.json').read_text(encoding='utf-8'))
assert actual == expected
