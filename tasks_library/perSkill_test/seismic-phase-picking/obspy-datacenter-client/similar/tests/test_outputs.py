import json
from pathlib import Path
requests = json.loads(Path('/root/data/retrieval_requests.json').read_text(encoding='utf-8'))
plans = []
for item in sorted(requests, key=lambda row: row['request_id']):
    if item['requires_response_archive']:
        plans.append({'request_id': item['request_id'], 'strategy_code': 'iris_special', 'service_family': 'response-format-service', 'client_target': 'iris', 'justification': 'response-format-special-case'})
    else:
        plans.append({'request_id': item['request_id'], 'strategy_code': 'standard_fdsn', 'service_family': 'fdsn-web-services', 'client_target': 'fdsn', 'justification': 'modern-common-service'})
expected = {'generated_from': {'request_count': len(requests)}, 'plans': plans}
actual = json.loads(Path('/root/similar_retrieval_plan.json').read_text(encoding='utf-8'))
assert actual == expected
