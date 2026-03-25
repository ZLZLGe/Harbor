#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

source = Path('/root/transfer3_source.mp4')
windows_path = Path('/root/data/transfer3_windows.json')
out_dir = Path('/root/transfer3_window_pack')
index_path = Path('/root/transfer3_window_index.json')


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


duration = ffprobe_duration(source)
windows = json.loads(windows_path.read_text(encoding='utf-8'))
out_dir.mkdir(parents=True, exist_ok=True)

normalized = []
for row in windows:
    start = max(0.0, float(row['start']))
    end = min(duration, float(row['end']))
    if end <= start:
        continue

    output_file = f"{row['window_id']}.mp4"
    clip_path = out_dir / output_file

    subprocess.run(
        [
            'ffmpeg', '-y', '-i', str(source),
            '-ss', f'{start:.3f}', '-to', f'{end:.3f}',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            str(clip_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    normalized.append(
        {
            'window_id': str(row['window_id']),
            'purpose': str(row['purpose']),
            'start': round(start, 3),
            'end': round(end, 3),
            'duration': round(end - start, 3),
            'output_file': output_file,
        }
    )

if not normalized:
    raise RuntimeError('No valid extraction windows after normalization')

index = {
    'source_video': source.name,
    'output_dir': out_dir.name,
    'windows': normalized,
    'total_windows': len(normalized),
    'total_duration_seconds': round(sum(item['duration'] for item in normalized), 3),
}
index_path.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
PY
