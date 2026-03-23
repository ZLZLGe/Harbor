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

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

skill_root = Path('')
for p in [
    '/root/.codex/skills',
    '/root/.claude/skills',
    '/root/.opencode/skill',
    '/root/.goose/skills',
    '/root/.factory/skills',
    '/root/.agents/skills',
    '/root/skills',
    '/root/.gemini/skills',
]:
    if Path(p, 'report-generator', 'scripts', 'generate_report.py').exists():
        skill_root = Path(p)
        break

if not skill_root:
    raise SystemExit('report-generator skill not found')

manifest = json.loads(Path('/root/data/candidate_manifest.json').read_text(encoding='utf-8'))
window = manifest['target_window']

candidates = []
for idx, item in enumerate(manifest['candidates']):
    out_path = Path(f'/tmp/candidate_report_{idx}.json')
    cmd = [
        'python3',
        str(skill_root / 'report-generator' / 'scripts' / 'generate_report.py'),
        '--original',
        '/root/data/master_source.mp4',
        '--compressed',
        item['compressed'],
        '--segments',
        item['segments'],
        '--output',
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    report = json.loads(out_path.read_text(encoding='utf-8'))
    candidates.append({'candidate_id': item['candidate_id'], 'report': report})

in_window = []
for c in candidates:
    pct = float(c['report']['compression_percentage'])
    if float(window['min_pct']) <= pct <= float(window['max_pct']):
        in_window.append(c)

if not in_window:
    raise SystemExit('no candidates in target window')

selected = min(
    in_window,
    key=lambda c: (abs(float(c['report']['compression_percentage']) - float(window['target_pct'])), c['candidate_id']),
)

result = {
    'target_window': window,
    'candidates': candidates,
    'selected_candidate': selected['candidate_id'],
    'selected_report': selected['report'],
}

Path('/root/transfer3_candidate_selection.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
PY
