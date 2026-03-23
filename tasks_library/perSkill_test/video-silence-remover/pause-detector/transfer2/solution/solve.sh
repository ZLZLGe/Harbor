#!/bin/bash
set -euo pipefail

SKILL_SCRIPT=""
for d in /root/.codex/skills /root/.claude/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/skills /root/.gemini/skills; do
  if [ -f "$d/pause-detector/scripts/detect_pauses.py" ]; then
    SKILL_SCRIPT="$d/pause-detector/scripts/detect_pauses.py"
    break
  fi
done

if [ -z "$SKILL_SCRIPT" ]; then
  echo "pause-detector skill not found" >&2
  exit 1
fi

for src in /root/data/transfer2_room_a.json /root/data/transfer2_room_b.json /root/data/transfer2_room_c.json; do
  name=$(basename "$src" .json)
  python3 "$SKILL_SCRIPT" \
    --energies "$src" \
    --start-time 1 \
    --threshold-ratio 0.58 \
    --min-duration 2 \
    --window-size 5 \
    --output "/tmp/${name}_pauses.json"
done

python3 - <<'PY'
import csv
import json
from pathlib import Path

inputs = [
    Path('/root/data/transfer2_room_a.json'),
    Path('/root/data/transfer2_room_b.json'),
    Path('/root/data/transfer2_room_c.json'),
]

rows = []
for src in inputs:
    source = json.loads(src.read_text(encoding='utf-8'))
    name = src.stem
    pauses = json.loads(Path(f'/tmp/{name}_pauses.json').read_text(encoding='utf-8'))['segments']
    count = len(pauses)
    first_start = pauses[0]['start'] if pauses else -1
    total = sum(seg['duration'] for seg in pauses)
    longest = max([seg['duration'] for seg in pauses], default=0)
    rows.append((source['session_id'], count, first_start, total, longest))

rows.sort(key=lambda row: row[0])

out_path = Path('/root/transfer2_pause_break_index.csv')
with out_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'session_id',
        'detected_break_count',
        'first_break_start',
        'total_pause_seconds',
        'longest_pause_seconds',
    ])
    writer.writerows(rows)
PY
