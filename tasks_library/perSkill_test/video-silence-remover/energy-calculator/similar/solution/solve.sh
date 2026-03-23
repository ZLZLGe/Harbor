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
  --audio /root/data/lesson_track.wav \
  --window-seconds 1 \
  --output /tmp/similar_energy_raw.json

python3 - <<'PY'
import json

raw = json.load(open('/tmp/similar_energy_raw.json', 'r', encoding='utf-8'))
energies = raw['energies']
report = {
    'track_id': 'lesson-track-a',
    'window_seconds': raw['window_seconds'],
    'energies': energies,
    'stats': raw['stats'],
    'quiet_seconds': [i for i, e in enumerate(energies) if e <= 50],
    'loudest_second': energies.index(max(energies)),
}
json.dump(report, open('/root/similar_energy_profile.json', 'w', encoding='utf-8'), indent=2)
PY
