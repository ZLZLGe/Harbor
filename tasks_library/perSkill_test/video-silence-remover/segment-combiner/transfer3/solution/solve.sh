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

python3 - <<'PY'
import csv
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path('/root/channel_manifest.json').read_text(encoding='utf-8'))
skill_script = Path('/root/.codex/skills/segment-combiner/scripts/combine_segments.py')
if not skill_script.exists():
    for root in [
        '/root/.claude/skills', '/root/.opencode/skill', '/root/.goose/skills',
        '/root/.factory/skills', '/root/.agents/skills', '/root/skills', '/root/.gemini/skills'
    ]:
        candidate = Path(root) / 'segment-combiner/scripts/combine_segments.py'
        if candidate.exists():
            skill_script = candidate
            break

rows = []
budget = int(manifest['budget_seconds'])

for channel in manifest['channels']:
    channel_id = channel['channel_id']
    tmp_output = Path(f"/tmp/{channel_id}_combined_segments.json")

    cmd = ['python3', str(skill_script), '--segments'] + channel['segment_files'] + ['--output', str(tmp_output)]
    subprocess.run(cmd, check=True)

    combined = json.loads(tmp_output.read_text(encoding='utf-8'))
    total_segments = int(combined['total_segments'])
    total_duration = int(combined['total_duration_seconds'])

    rows.append({
        'channel_id': channel_id,
        'total_segments': total_segments,
        'total_duration_seconds': total_duration,
        'budget_seconds': budget,
        'over_budget': 'yes' if total_duration > budget else 'no',
    })

rows.sort(key=lambda r: (-r['total_duration_seconds'], r['channel_id']))
for idx, row in enumerate(rows, start=1):
    row['rank'] = idx

with Path('/root/transfer3_trim_budget_report.csv').open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            'channel_id',
            'total_segments',
            'total_duration_seconds',
            'budget_seconds',
            'over_budget',
            'rank',
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
PY
