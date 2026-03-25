#!/bin/bash
set -euo pipefail

python3 << 'PY'
import json
from pathlib import Path

single = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
phrases = ["you know", "i mean", "kind of", "i guess"]
lead_in = 0.05
merge_gap = 0.1
word_durations = {
    'uh': 0.30,
    'um': 0.40,
    'hum': 0.60,
    'hmm': 0.60,
    'mhm': 0.55,
    'like': 0.30,
    'yeah': 0.35,
    'so': 0.25,
    'well': 0.35,
    'okay': 0.40,
    'basically': 0.55,
    'you know': 0.55,
    'i mean': 0.50,
    'kind of': 0.50,
    'i guess': 0.50,
}
default_duration = 0.40

payload = json.loads(Path('/root/data/transfer3_panel_segments.json').read_text(encoding='utf-8'))
words = []
for seg in payload['segments']:
    words.extend(seg['words'])
words.sort(key=lambda x: x['start'])

norm = [''.join(ch for ch in item['word'].lower().strip() if ch.isalnum()) for item in words]

hits = []
for i, item in enumerate(words):
    w = norm[i]
    if w in single:
        hits.append({'word': w, 'timestamp': float(item['start'])})
for i in range(len(words) - 1):
    phrase = f"{norm[i]} {norm[i+1]}"
    if phrase in phrases:
        hits.append({'word': phrase, 'timestamp': float(words[i]['start'])})

seen = set()
ordered_hits = []
for hit in sorted(hits, key=lambda x: x['timestamp']):
    key = (hit['word'], round(hit['timestamp'], 2))
    if key in seen:
        continue
    seen.add(key)
    ordered_hits.append({'word': hit['word'], 'timestamp': round(hit['timestamp'], 2)})

raw = []
for hit in ordered_hits:
    ts = hit['timestamp']
    dur = word_durations.get(hit['word'], default_duration)
    raw.append(
        {
            'start': max(0.0, ts - lead_in),
            'end': ts + dur,
            'trigger': hit['word'],
        }
    )

merged = []
for clip in raw:
    if not merged:
        merged.append(clip)
        continue
    prev = merged[-1]
    if clip['start'] <= prev['end'] + merge_gap:
        prev['end'] = max(prev['end'], clip['end'])
    else:
        merged.append(clip)

clips = []
for item in merged:
    start = round(item['start'], 2)
    end = round(item['end'], 2)
    clips.append(
        {
            'start': start,
            'end': end,
            'duration': round(end - start, 2),
            'trigger': item['trigger'],
        }
    )

total_duration = round(sum(item['duration'] for item in clips), 2)
out = {
    'clip_parameters': {
        'lead_in_seconds': lead_in,
        'merge_gap_seconds': merge_gap,
        'word_durations': word_durations,
    },
    'clips': clips,
    'total_clips': len(clips),
    'total_duration_seconds': total_duration,
}

Path('/root/transfer3_clip_plan.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
PY
