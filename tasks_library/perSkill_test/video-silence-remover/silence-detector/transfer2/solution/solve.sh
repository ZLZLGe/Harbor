#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

policy = json.loads(Path('/root/trim_policy.json').read_text(encoding='utf-8'))

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

silence_path = Path('/tmp/trim_intro_silence.json')
subprocess.run([
    'python3', str(script),
    '--energies', policy['energies_file'],
    '--output', str(silence_path),
    '--threshold-multiplier', str(policy['threshold_multiplier']),
    '--initial-window', str(policy['initial_window']),
    '--smoothing-window', str(policy['smoothing_window']),
], check=True)

silence = json.loads(silence_path.read_text(encoding='utf-8'))
detected_end = int(silence['total_duration_seconds'])

publish_start = detected_end + int(policy['safety_buffer_seconds'])
publish_start = max(int(policy['min_publish_start_second']), publish_start)
publish_start = min(int(policy['max_publish_start_second']), publish_start)

out = {
    'detected_intro_end_seconds': detected_end,
    'publish_start_seconds': publish_start,
    'cut_segment': {
        'start': 0,
        'end': publish_start,
        'duration': publish_start,
    },
    'policy_applied': {
        'safety_buffer_seconds': int(policy['safety_buffer_seconds']),
        'min_publish_start_second': int(policy['min_publish_start_second']),
        'max_publish_start_second': int(policy['max_publish_start_second']),
    },
}

Path('/root/intro_trim_plan.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
PY
