#!/bin/bash
set -euo pipefail

SKILL_ROOT=""
for d in /root/.codex/skills /root/.claude/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/skills /root/.gemini/skills; do
  if [ -f "$d/report-generator/scripts/generate_report.py" ]; then
    SKILL_ROOT="$d"
    break
  fi
done

if [ -z "$SKILL_ROOT" ]; then
  echo "report-generator skill not found" >&2
  exit 1
fi

python3 "$SKILL_ROOT/report-generator/scripts/generate_report.py" \
  --original /root/data/source_session.mp4 \
  --compressed /root/data/trimmed_session.mp4 \
  --segments /root/data/segments_removed.json \
  --output /root/similar_compression_report.json
