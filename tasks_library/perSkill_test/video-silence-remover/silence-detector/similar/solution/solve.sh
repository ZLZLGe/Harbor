#!/bin/bash
set -euo pipefail

SKILL_ROOT=""
for d in /root/.codex/skills /root/.claude/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/skills /root/.gemini/skills; do
  if [ -f "$d/silence-detector/scripts/detect_silence.py" ]; then
    SKILL_ROOT="$d"
    break
  fi
done

if [ -z "$SKILL_ROOT" ]; then
  echo "silence-detector skill not found" >&2
  exit 1
fi

read -r ENERGIES TM IW SW < <(
  python3 - <<'PY'
import json
cfg = json.load(open('/root/detection_config.json', 'r', encoding='utf-8'))
print(cfg['energies_file'], cfg['threshold_multiplier'], cfg['initial_window'], cfg['smoothing_window'])
PY
)

python3 "$SKILL_ROOT/silence-detector/scripts/detect_silence.py" \
  --energies "$ENERGIES" \
  --output /root/initial_silence_report.json \
  --threshold-multiplier "$TM" \
  --initial-window "$IW" \
  --smoothing-window "$SW"
