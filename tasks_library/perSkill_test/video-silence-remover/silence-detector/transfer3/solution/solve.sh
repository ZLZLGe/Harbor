#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path('/root/qc_manifest.json').read_text(encoding='utf-8'))

detect = manifest['detection']
policy = manifest['qc_policy']

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

records_out = []
summary = {'ok': 0, 'review': 0, 'reject': 0, 'total': 0}

for record in manifest['records']:
    tmp = Path(f"/tmp/{record['recording_id']}_silence.json")
    subprocess.run([
        'python3', str(script),
        '--energies', record['energies_file'],
        '--output', str(tmp),
        '--threshold-multiplier', str(detect['threshold_multiplier']),
        '--initial-window', str(detect['initial_window']),
        '--smoothing-window', str(detect['smoothing_window']),
    ], check=True)

    silence = json.loads(tmp.read_text(encoding='utf-8'))
    seconds = int(silence['total_duration_seconds'])

    if seconds <= int(policy['ok_max_seconds']):
        flag = 'ok'
    elif seconds <= int(policy['review_max_seconds']):
        flag = 'review'
    else:
        flag = 'reject'

    records_out.append({
        'recording_id': record['recording_id'],
        'silence_seconds': seconds,
        'qc_flag': flag,
    })
    summary[flag] += 1
    summary['total'] += 1

out = {
    'records': records_out,
    'summary': summary,
}

Path('/root/silence_qc_flags.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
PY
