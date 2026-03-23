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
  --energies /root/data/transfer1_board_session_energies.json \
  --start-time 2 \
  --threshold-ratio 0.6 \
  --min-duration 2 \
  --window-size 7 \
  --output /tmp/transfer1_raw_pauses.json

python3 - <<'PY'
import json
from pathlib import Path

input_data = json.loads(Path('/root/data/transfer1_board_session_energies.json').read_text(encoding='utf-8'))
raw = json.loads(Path('/tmp/transfer1_raw_pauses.json').read_text(encoding='utf-8'))
segments = raw['segments']

total = sum(seg['duration'] for seg in segments)
longest = max([seg['duration'] for seg in segments], default=0)
top_two = sorted(segments, key=lambda s: (-s['duration'], s['start']))[:2]

result = {
    'session_id': input_data['session_id'],
    'parameters': {
        'start_time': 2,
        'threshold_ratio': 0.6,
        'min_duration': 2,
        'window_size': 7,
    },
    'pause_segments': segments,
    'total_pause_seconds': total,
    'longest_pause_seconds': longest,
    'top_two_segments': top_two,
    'qa_flag': 'needs-review' if longest >= 4 else 'ok',
}

Path('/root/transfer1_editorial_pause_audit.json').write_text(
    json.dumps(result, indent=2),
    encoding='utf-8',
)
PY
