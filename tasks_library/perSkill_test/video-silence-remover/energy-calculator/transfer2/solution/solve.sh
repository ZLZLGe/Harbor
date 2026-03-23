#!/bin/bash
set -euo pipefail

SKILL_ROOT=""
for d in /root/.codex/skills /root/.claude/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/skills /root/.gemini/skills; do
  if [ -f "$d/energy-calculator/scripts/calc_energy.py" ]; then
    SKILL_ROOT="$d"
    break
  fi
done

if [ -z "$SKILL_ROOT" ]; then
  echo "energy-calculator skill not found" >&2
  exit 1
fi

python3 "$SKILL_ROOT/energy-calculator/scripts/calc_energy.py" \
  --audio /root/data/night_watch.wav \
  --window-seconds 1 \
  --output /tmp/transfer2_energy_raw.json

python3 - <<'PY'
import json

threshold = 15
raw = json.load(open('/tmp/transfer2_energy_raw.json', 'r', encoding='utf-8'))
energies = raw['energies']
quiet_flags = [e <= threshold for e in energies]
intervals = []
start = None
for i, is_quiet in enumerate(quiet_flags):
    if is_quiet and start is None:
        start = i
    if not is_quiet and start is not None:
        intervals.append({'start': start, 'end': i, 'duration': i - start})
        start = None
if start is not None:
    intervals.append({'start': start, 'end': len(energies), 'duration': len(energies) - start})

report = {
    'recording_id': 'night-watch-3',
    'window_seconds': raw['window_seconds'],
    'quiet_threshold': threshold,
    'energies': energies,
    'quiet_intervals': intervals,
    'total_quiet_seconds': sum(item['duration'] for item in intervals),
}
json.dump(report, open('/root/transfer2_quiet_intervals.json', 'w', encoding='utf-8'), indent=2)
PY
