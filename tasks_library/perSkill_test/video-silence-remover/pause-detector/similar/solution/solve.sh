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
        '/root/.codex/skills/pause-detector/scripts/detect_pauses.py',
        '--energies',
        config['input_energies'],
        '--output',
        config['output_json'],
        '--start-time',
        str(config['start_time']),
        '--threshold-ratio',
        str(config['threshold_ratio']),
        '--min-duration',
        str(config['min_duration']),
        '--window-size',
        str(config['window_size']),
    ],
    check=True,
)

pauses = json.loads(Path(config['output_json']).read_text())
segments = pauses['segments']
longest = max(segments, key=lambda segment: (segment['duration'], -segment['start']))
summary = {
    'pause_count': pauses['total_segments'],
    'total_pause_duration': pauses['total_duration_seconds'],
    'longest_pause_start': longest['start'],
    'longest_pause_duration': longest['duration'],
    'analysis_start_time': config['start_time'],
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
