#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

source = Path('/root/similar_source.mp4')
windows_path = Path('/root/data/similar_filler_windows.json')
output_video = Path('/root/similar_filler_montage.mp4')
report_path = Path('/root/similar_filler_windows_report.json')

windows = json.loads(windows_path.read_text(encoding='utf-8'))
windows = sorted(windows, key=lambda item: float(item['start']))

work = Path('/tmp/similar_segments')
work.mkdir(parents=True, exist_ok=True)
segment_files = []

for idx, window in enumerate(windows, start=1):
    start = float(window['start'])
    end = float(window['end'])
    seg_path = work / f'segment_{idx:03d}.mp4'
    subprocess.run(
        [
            'ffmpeg', '-y', '-i', str(source),
            '-ss', f'{start:.3f}', '-to', f'{end:.3f}',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            str(seg_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    segment_files.append(seg_path)

list_path = work / 'segments.txt'
with list_path.open('w', encoding='utf-8') as handle:
    for seg in segment_files:
        handle.write(f"file '{seg}'\n")

subprocess.run(
    [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(list_path),
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        str(output_video),
    ],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

expected_total = round(sum(float(item['end']) - float(item['start']) for item in windows), 3)
report = {
    'source_video': source.name,
    'output_video': output_video.name,
    'segments_used': windows,
    'total_segments': len(windows),
    'total_duration_seconds': expected_total,
}
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
PY
