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
  --original /root/data/original_briefing.mp4 \
  --compressed /root/data/trimmed_briefing.mp4 \
  --output /tmp/base_report.json

python3 - <<'PY'
import json
from pathlib import Path

policy = json.loads(Path('/root/data/governance_policy.json').read_text(encoding='utf-8'))
base = json.loads(Path('/tmp/base_report.json').read_text(encoding='utf-8'))
base['segments_removed'] = []
removed = float(base['removed_duration_seconds'])
minimum = float(policy['minimum_removed_seconds'])

out = {
    'report_id': policy['report_id'],
    'source_asset': policy['source_asset'],
    'compression_report': base,
    'quality_gate': {
        'minimum_removed_seconds': policy['minimum_removed_seconds'],
        'passed': removed >= minimum,
    },
}

Path('/root/transfer1_governance_report.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
PY
