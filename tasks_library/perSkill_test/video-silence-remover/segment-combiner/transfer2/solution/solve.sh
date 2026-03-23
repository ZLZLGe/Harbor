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
  --segments /root/schedule_segments.json /root/compliance_segments.json \
  --output /tmp/transfer2_all_segments.json

python3 - <<'PY'
import json
from pathlib import Path

combined = json.loads(Path('/tmp/transfer2_all_segments.json').read_text(encoding='utf-8'))
segments = combined['segments']

alerts = []
overlap_indexes = set()
for i in range(len(segments) - 1):
    first = segments[i]
    second = segments[i + 1]
    overlap_start = max(first['start'], second['start'])
    overlap_end = min(first['end'], second['end'])
    if overlap_end > overlap_start:
        alerts.append({
            'first_segment': first,
            'second_segment': second,
            'overlap': {
                'start': overlap_start,
                'end': overlap_end,
                'duration': overlap_end - overlap_start,
            },
        })
        overlap_indexes.add(i)
        overlap_indexes.add(i + 1)

non_overlapping = [seg for idx, seg in enumerate(segments) if idx not in overlap_indexes]

output = {
    'total_segments': int(combined['total_segments']),
    'total_duration_seconds': int(combined['total_duration_seconds']),
    'has_overlaps': len(alerts) > 0,
    'overlap_alerts': alerts,
    'non_overlapping_segments': non_overlapping,
}

Path('/root/transfer2_overlap_alerts.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
PY
