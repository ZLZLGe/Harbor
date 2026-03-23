#!/bin/bash
set -euo pipefail

SKILL_SCRIPT=""
for d in /root/.codex/skills /root/.claude/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/skills /root/.gemini/skills; do
  if [ -f "$d/segment-combiner/scripts/combine_segments.py" ]; then
    SKILL_SCRIPT="$d/segment-combiner/scripts/combine_segments.py"
    break
  fi
done

if [ -z "$SKILL_SCRIPT" ]; then
  echo "segment-combiner skill not found" >&2
  exit 1
fi

python3 "$SKILL_SCRIPT" \
  --segments /root/intro_segments.json /root/pause_segments.json \
  --output /root/similar_combined_segments.json
