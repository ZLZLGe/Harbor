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
  --audio /root/data/line_a.wav \
  --window-seconds 1 \
  --output /tmp/transfer3_a.json

python3 "$SKILL_ROOT/energy-calculator/scripts/calc_energy.py" \
  --audio /root/data/line_b.wav \
  --window-seconds 1 \
  --output /tmp/transfer3_b.json

python3 - <<'PY'
import json

a = json.load(open('/tmp/transfer3_a.json', 'r', encoding='utf-8'))['energies']
b = json.load(open('/tmp/transfer3_b.json', 'r', encoding='utf-8'))['energies']
if len(a) != len(b):
    raise SystemExit('energy length mismatch between line_a and line_b')

delta = [x - y for x, y in zip(a, b)]
baseline_mean = sum(a) / len(a)
candidate_mean = sum(b) / len(b)
report = {
    'comparison_id': 'line-a-vs-line-b',
    'window_seconds': 1,
    'baseline_mean': baseline_mean,
    'candidate_mean': candidate_mean,
    'reduction_ratio': (baseline_mean - candidate_mean) / baseline_mean,
    'per_second_delta': delta,
    'improved_seconds': [i for i, d in enumerate(delta) if d > 0],
}
json.dump(report, open('/root/transfer3_energy_delta.json', 'w', encoding='utf-8'), indent=2)
PY
