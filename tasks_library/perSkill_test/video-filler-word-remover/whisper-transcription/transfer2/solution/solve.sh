#!/bin/bash
set -euo pipefail

python3 << 'PY'
import json
from collections import Counter
from pathlib import Path

single = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
phrases = ["you know", "i mean", "kind of", "i guess"]

turns = json.loads(Path('/root/data/transfer2_support_turns.json').read_text(encoding='utf-8'))
words = []
for turn in turns:
    words.extend(turn['words'])
words.sort(key=lambda x: x['start'])

norm = [''.join(ch for ch in item['word'].lower().strip() if ch.isalnum()) for item in words]

hits = []
for i, item in enumerate(words):
    w = norm[i]
    if w in single:
        hits.append((w, float(item['start'])))
for i in range(len(words) - 1):
    phrase = f"{norm[i]} {norm[i+1]}"
    if phrase in phrases:
        hits.append((phrase, float(words[i]['start'])))

hits = sorted(set((word, round(ts, 2)) for word, ts in hits), key=lambda x: x[1])
max_ts = max((ts for _, ts in hits), default=0.0)
window_size = 30
num_windows = int(max_ts // window_size) + 1

windows = []
for idx in range(num_windows):
    start = idx * window_size
    end = start + window_size
    in_window = [(word, ts) for word, ts in hits if start <= ts < end]
    count = len(in_window)
    density = round(count * 2.0, 2)
    if count == 0:
        dominant = ''
    else:
        counter = Counter(word for word, _ in in_window)
        top_count = max(counter.values())
        dominant = sorted(word for word, c in counter.items() if c == top_count)[0]
    windows.append(
        {
            'window_start': start,
            'window_end': end,
            'filler_count': count,
            'density_per_minute': density,
            'dominant_filler': dominant,
        }
    )

peak_count = max((item['filler_count'] for item in windows), default=0)
peak_start = min((item['window_start'] for item in windows if item['filler_count'] == peak_count), default=0)

out = {
    'window_size_seconds': window_size,
    'windows': windows,
    'peak_window_start': peak_start,
    'peak_window_count': peak_count,
}

Path('/root/transfer2_window_report.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
PY
