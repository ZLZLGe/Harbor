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
  --segments /root/reviewer_a_segments.json /root/reviewer_b_segments.json /root/reviewer_c_segments.json \
  --output /root/transfer1_all_segments.json

python3 - <<'PY'
import json
from pathlib import Path

inputs = [
    ('reviewer_a', Path('/root/reviewer_a_segments.json')),
    ('reviewer_b', Path('/root/reviewer_b_segments.json')),
    ('reviewer_c', Path('/root/reviewer_c_segments.json')),
]

combined = json.loads(Path('/root/transfer1_all_segments.json').read_text(encoding='utf-8'))
segments = combined['segments']

reviewer_stats = []
for reviewer, path in inputs:
    data = json.loads(path.read_text(encoding='utf-8'))
    duration = sum(int(seg['duration']) for seg in data['segments'])
    reviewer_stats.append({
        'reviewer': reviewer,
        'segment_count': len(data['segments']),
        'duration_seconds': duration,
    })

manifest = {
    'segment_files_used': [
        '/root/reviewer_a_segments.json',
        '/root/reviewer_b_segments.json',
        '/root/reviewer_c_segments.json',
    ],
    'combined_segments_output': '/root/transfer1_all_segments.json',
    'total_segments': int(combined['total_segments']),
    'total_duration_seconds': int(combined['total_duration_seconds']),
    'max_single_segment_seconds': max(int(seg['duration']) for seg in segments),
    'reviewer_stats': reviewer_stats,
}

Path('/root/transfer1_review_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
PY
