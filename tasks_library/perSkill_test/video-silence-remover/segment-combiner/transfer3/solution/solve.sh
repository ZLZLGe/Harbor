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
        '/root/.codex/skills/segment-combiner/scripts/combine_segments.py',
        '--segments',
        *config['input_segments'],
        '--output',
        config['output_json'],
    ],
    check=True,
)

payload = json.loads(Path(config['output_json']).read_text())
segments = payload['segments']
summary = {
    'segment_count': payload['total_segments'],
    'total_duration_seconds': payload['total_duration_seconds'],
    'first_segment_start': segments[0]['start'],
    'last_segment_end': segments[-1]['end'],
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
