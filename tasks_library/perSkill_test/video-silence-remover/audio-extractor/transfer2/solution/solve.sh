#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
import wave
from pathlib import Path

config = json.loads(Path('/root/data/task_config.json').read_text())

cmd = [
    'python3',
    '/root/.codex/skills/audio-extractor/scripts/extract_audio.py',
    '--video',
    config['input_video'],
    '--output',
    config['output_wav'],
    '--sample-rate',
    str(config['sample_rate']),
]
if config.get('duration_limit') is not None:
    cmd.extend(['--duration', str(config['duration_limit'])])

subprocess.run(cmd, check=True)

with wave.open(config['output_wav'], 'rb') as wav_file:
    frame_count = wav_file.getnframes()
    sample_rate = wav_file.getframerate()
    channels = wav_file.getnchannels()
    sample_width = wav_file.getsampwidth()

duration_seconds = frame_count / sample_rate if sample_rate else 0.0
summary = {
    'sample_rate': sample_rate,
    'channels': channels,
    'sample_width_bytes': sample_width,
    'frame_count': frame_count,
    'duration_seconds': round(duration_seconds, 3),
}
Path(config['summary_json']).write_text(json.dumps(summary, indent=2) + '\n')
PY
