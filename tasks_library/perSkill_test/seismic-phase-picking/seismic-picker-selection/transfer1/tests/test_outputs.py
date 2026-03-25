import csv
from pathlib import Path
mapping = {'tiny-known': ('template_matching', 'deep_learning', 'manual', 'sta_lta'), 'sparse-unknown': ('deep_learning', 'manual', 'sta_lta', 'template_matching'), 'rapid-screen': ('sta_lta', 'deep_learning', 'manual', 'template_matching'), 'quality-audit': ('manual', 'deep_learning', 'template_matching', 'sta_lta')}
expected = []
with Path('/root/data/ranking_cases.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        rank = mapping[item['priority_code']]
        expected.append({'case_id': item['case_id'], 'first_choice': rank[0], 'second_choice': rank[1], 'third_choice': rank[2], 'fourth_choice': rank[3]})
with Path('/root/transfer1_method_ranking.csv').open(encoding='utf-8', newline='') as handle:
    actual = list(csv.DictReader(handle))
assert actual == expected
