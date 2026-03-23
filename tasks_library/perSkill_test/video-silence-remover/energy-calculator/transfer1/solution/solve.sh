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
  --audio /root/data/broadcast_clip.wav \
  --window-seconds 0.5 \
  --output /tmp/transfer1_energy_raw.json

python3 - <<'PY'
import json

raw = json.load(open('/tmp/transfer1_energy_raw.json', 'r', encoding='utf-8'))
energies = raw['energies']
peak = max(energies)
report = {
    'clip_id': 'broadcast-17',
    'window_seconds': raw['window_seconds'],
    'energies': energies,
    'peak_windows': [i for i, e in enumerate(energies) if e == peak],
    'alert_windows': [i for i, e in enumerate(energies) if e >= 140],
    'mean_energy': sum(energies) / len(energies),
}
json.dump(report, open('/root/transfer1_energy_alerts.json', 'w', encoding='utf-8'), indent=2)
PY
