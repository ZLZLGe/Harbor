#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

config = json.loads(Path('/root/data/task_config.json').read_text())

subprocess.run(
    [
        'python3',
        '/root/.codex/skills/silence-detector/scripts/detect_silence.py',
        '--energies',
        config['input_energies'],
        '--output',
        config['output_json'],
        '--threshold-multiplier',
        str(config['threshold_multiplier']),
        '--initial-window',
        str(config['initial_window']),
        '--smoothing-window',
        str(config['smoothing_window']),
    ],
    check=True,
)

payload = json.loads(Path(config['output_json']).read_text())
analysis = payload['analysis']
summary = {
    'detected_silence_end': payload['total_duration_seconds'],
    'baseline_energy': analysis['initial_avg'],
    'threshold': analysis['threshold'],
    'has_initial_silence': payload['total_segments'] > 0,
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
