#!/bin/bash
set -euo pipefail

python3 << 'PY'
import json
from collections import defaultdict
from pathlib import Path

single = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
phrases = ["you know", "i mean", "kind of", "i guess"]

payload = json.loads(Path('/root/data/transfer1_meeting_words.json').read_text(encoding='utf-8'))
words = payload['words']
norm = [''.join(ch for ch in item['word'].lower().strip() if ch.isalnum()) for item in words]

hits = []
for i, item in enumerate(words):
    w = norm[i]
    if w in single:
        hits.append((w, round(float(item['start']), 2)))
for i in range(len(words) - 1):
    phrase = f"{norm[i]} {norm[i+1]}"
    if phrase in phrases:
        hits.append((phrase, round(float(words[i]['start']), 2)))

hits = sorted(set(hits), key=lambda x: x[1])

agg = defaultdict(list)
for word, ts in hits:
    agg[word].append(ts)

by_word = []
for word, ts_list in agg.items():
    by_word.append(
        {
            'word': word,
            'count': len(ts_list),
            'first_timestamp': round(min(ts_list), 2),
            'last_timestamp': round(max(ts_list), 2),
        }
    )

by_word.sort(key=lambda x: (-x['count'], x['word']))

total_hits = sum(item['count'] for item in by_word)
if by_word:
    top = {'word': by_word[0]['word'], 'count': by_word[0]['count']}
else:
    top = {'word': '', 'count': 0}

out = {
    'total_hits': total_hits,
    'by_word': by_word,
    'top_filler': top,
}

Path('/root/transfer1_filler_summary.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
PY
