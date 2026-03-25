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
        '/root/.codex/skills/report-generator/scripts/generate_report.py',
        '--original',
        config['original_video'],
        '--compressed',
        config['compressed_video'],
        '--segments',
        config['segments_json'],
        '--output',
        config['output_json'],
    ],
    check=True,
)

report = json.loads(Path(config['output_json']).read_text())
segment_data = json.loads(Path(config['segments_json']).read_text())
segments = segment_data['segments']
summary = {
    'segment_count': len(segments),
    'removed_duration_seconds': report['removed_duration_seconds'],
    'compression_percentage': report['compression_percentage'],
    'longest_segment_duration': max(segment['duration'] for segment in segments),
    'segment_total_duration_seconds': sum(segment['duration'] for segment in segments),
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
