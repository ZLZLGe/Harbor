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

python3 "$SKILL_SCRIPT" \
  --energies /root/data/similar_lecture_energies.json \
  --start-time 5 \
  --threshold-ratio 0.55 \
  --min-duration 2 \
  --window-size 5 \
  --output /root/similar_pause_segments.json
