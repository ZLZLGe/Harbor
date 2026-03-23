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

python3 - <<'PY'
import csv
import json
import subprocess
from pathlib import Path

cfg = json.loads(Path('/root/batch_config.json').read_text(encoding='utf-8'))
script = Path('/root/.codex/skills/silence-detector/scripts/detect_silence.py')
if not script.exists():
    for candidate in [
        '/root/.claude/skills', '/root/.opencode/skill', '/root/.goose/skills',
        '/root/.factory/skills', '/root/.agents/skills', '/root/skills', '/root/.gemini/skills'
    ]:
        candidate_script = Path(candidate) / 'silence-detector/scripts/detect_silence.py'
        if candidate_script.exists():
            script = candidate_script
            break

rows = []
for clip in cfg['clips']:
    tmp = Path(f"/tmp/{clip['clip_id']}_silence.json")
    cmd = [
        'python3', str(script),
        '--energies', clip['energies_file'],
        '--output', str(tmp),
        '--threshold-multiplier', str(cfg['threshold_multiplier']),
        '--initial-window', str(cfg['initial_window']),
        '--smoothing-window', str(cfg['smoothing_window']),
    ]
    subprocess.run(cmd, check=True)
    result = json.loads(tmp.read_text(encoding='utf-8'))
    silence_seconds = int(result['total_duration_seconds'])
    rows.append({
        'clip_id': clip['clip_id'],
        'silence_seconds': silence_seconds,
        'has_preroll': 'yes' if silence_seconds > 0 else 'no',
    })

rows.sort(key=lambda r: (-r['silence_seconds'], r['clip_id']))
for idx, row in enumerate(rows, start=1):
    row['rank'] = idx

with Path('/root/pre_roll_leaderboard.csv').open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['clip_id', 'silence_seconds', 'has_preroll', 'rank'])
    writer.writeheader()
    writer.writerows(rows)
PY
