#!/bin/bash
set -euo pipefail

python3 << 'PY'
import json
from pathlib import Path

single = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
phrases = ["you know", "i mean", "kind of", "i guess"]

inp = Path('/root/data/similar_transcript_words.json')
out = Path('/root/similar_annotations.json')
words = json.loads(inp.read_text(encoding='utf-8'))

norm = [''.join(ch for ch in item['word'].lower().strip() if ch.isalnum()) for item in words]

annotations = []
for i, item in enumerate(words):
    w = norm[i]
    ts = round(float(item['start']), 2)
    if w in single:
        annotations.append({'word': w, 'timestamp': ts})

for i in range(len(words) - 1):
    a = norm[i]
    b = norm[i + 1]
    phrase = f"{a} {b}"
    if phrase in phrases:
        annotations.append({'word': phrase, 'timestamp': round(float(words[i]['start']), 2)})

annotations.sort(key=lambda x: x['timestamp'])
seen = set()
unique = []
for item in annotations:
    key = (item['word'], item['timestamp'])
    if key in seen:
        continue
    seen.add(key)
    unique.append(item)

out.write_text(json.dumps(unique, indent=2), encoding='utf-8')
PY
