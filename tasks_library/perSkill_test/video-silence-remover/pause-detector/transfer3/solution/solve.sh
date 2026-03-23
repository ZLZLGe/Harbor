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
  --energies /root/data/transfer3_narration_track.json \
  --start-time 0 \
  --threshold-ratio 0.56 \
  --min-duration 2 \
  --window-size 5 \
  --output /tmp/transfer3_narration_pauses.json

python3 "$SKILL_SCRIPT" \
  --energies /root/data/transfer3_screen_track.json \
  --start-time 0 \
  --threshold-ratio 0.60 \
  --min-duration 2 \
  --window-size 5 \
  --output /tmp/transfer3_screen_pauses.json

python3 - <<'PY'
import json
from pathlib import Path

narration = json.loads(Path('/tmp/transfer3_narration_pauses.json').read_text(encoding='utf-8'))['segments']
screen = json.loads(Path('/tmp/transfer3_screen_pauses.json').read_text(encoding='utf-8'))['segments']

overlap = []
i = 0
j = 0
while i < len(narration) and j < len(screen):
    n = narration[i]
    s = screen[j]
    start = max(n['start'], s['start'])
    end = min(n['end'], s['end'])
    if start < end:
        overlap.append({'start': start, 'end': end, 'duration': end - start})

    if n['end'] <= s['end']:
        i += 1
    else:
        j += 1

result = {
    'narration_segments': narration,
    'screen_segments': screen,
    'overlap_segments': overlap,
    'overlap_duration_seconds': sum(seg['duration'] for seg in overlap),
    'joint_pause_count': len(overlap),
}

Path('/root/transfer3_overlap_windows.json').write_text(
    json.dumps(result, indent=2),
    encoding='utf-8',
)
PY
