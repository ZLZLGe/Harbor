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
        '/root/.codex/skills/video-processor/scripts/process_video.py',
        '--input',
        config['input_video'],
        '--output',
        config['output_video'],
        '--remove-segments',
        *config['remove_segments'],
    ],
    check=True,
)

report = json.loads(Path(config['report_json']).read_text())
summary = {
    'output_duration': report['output_duration'],
    'removed_duration': report['removed_duration'],
    'segments_removed': report['segments_removed'],
    'segments_kept': report['segments_kept'],
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
