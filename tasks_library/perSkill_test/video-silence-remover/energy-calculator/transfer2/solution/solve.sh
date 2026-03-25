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
        '/root/.codex/skills/energy-calculator/scripts/calc_energy.py',
        '--audio',
        config['input_audio'],
        '--output',
        config['output_json'],
        '--window-seconds',
        str(config['window_seconds']),
    ],
    check=True,
)

energy_data = json.loads(Path(config['output_json']).read_text())
energies = energy_data['energies']
summary = {
    'window_count': len(energies),
    'loudest_window_index': max(range(len(energies)), key=lambda idx: energies[idx]),
    'quietest_window_index': min(range(len(energies)), key=lambda idx: energies[idx]),
    'active_window_count': sum(1 for value in energies if value >= config['activity_threshold']),
    'activity_threshold': config['activity_threshold'],
    'mean_energy': energy_data['stats']['mean'],
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
