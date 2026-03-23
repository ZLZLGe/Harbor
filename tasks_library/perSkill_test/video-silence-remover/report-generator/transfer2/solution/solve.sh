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

manifest = json.loads(Path('/root/data/batch_manifest.json').read_text(encoding='utf-8'))
reports = []

for idx, job in enumerate(manifest['jobs']):
    out_path = Path(f'/tmp/job_report_{idx}.json')
    cmd = [
        'python3',
        str(skill_root / 'report-generator' / 'scripts' / 'generate_report.py'),
        '--original',
        job['original'],
        '--compressed',
        job['compressed'],
        '--output',
        str(out_path),
    ]
    if 'segments' in job:
        cmd.extend(['--segments', job['segments']])

    subprocess.run(cmd, check=True)
    report = json.loads(out_path.read_text(encoding='utf-8'))
    if 'segments' not in job:
        report['segments_removed'] = []

    reports.append({
        'clip_id': job['clip_id'],
        'report': report,
    })

sum_original = sum(float(x['report']['original_duration_seconds']) for x in reports)
sum_compressed = sum(float(x['report']['compressed_duration_seconds']) for x in reports)
sum_removed = sum(float(x['report']['removed_duration_seconds']) for x in reports)
mean_pct = sum(float(x['report']['compression_percentage']) for x in reports) / len(reports)

result = {
    'batch_id': manifest['batch_id'],
    'reports': reports,
    'portfolio': {
        'total_original_seconds': round(sum_original, 2),
        'total_compressed_seconds': round(sum_compressed, 2),
        'total_removed_seconds': round(sum_removed, 2),
        'mean_compression_percentage': round(mean_pct, 2),
    },
}

Path('/root/transfer2_batch_summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
PY
