#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import subprocess
from pathlib import Path

source = Path('/root/transfer2_source.mp4')
chapters_path = Path('/root/data/transfer2_chapters.json')
clips_dir = Path('/root/transfer2_clips')
manifest_path = Path('/root/transfer2_sampler_manifest.csv')
reel_path = Path('/root/transfer2_sampler_reel.mp4')
clip_length = 2.4


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
chapters = json.loads(chapters_path.read_text(encoding='utf-8'))
clips_dir.mkdir(parents=True, exist_ok=True)

rows = []
clip_paths = []
for idx, chapter in enumerate(chapters, start=1):
    start = float(chapter['start'])
    if start >= duration:
        continue
    end = min(start + clip_length, duration)
    if end <= start:
        continue

    clip_name = f'clip_{idx:02d}_{chapter["chapter_id"]}.mp4'
    clip_path = clips_dir / clip_name

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

    row = {
        'clip_name': clip_name,
        'chapter_id': str(chapter['chapter_id']),
        'topic': str(chapter['topic']),
        'start': f'{start:.3f}',
        'end': f'{end:.3f}',
        'clip_duration': f'{(end - start):.3f}',
    }
    rows.append(row)
    clip_paths.append(clip_path)

with manifest_path.open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=['clip_name', 'chapter_id', 'topic', 'start', 'end', 'clip_duration'],
    )
    writer.writeheader()
    writer.writerows(rows)

if clip_paths:
    list_path = Path('/tmp/transfer2_concat_list.txt')
    with list_path.open('w', encoding='utf-8') as handle:
        for clip_path in clip_paths:
            handle.write(f"file '{clip_path}'\n")

    subprocess.run(
        [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_path),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            str(reel_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
else:
    raise RuntimeError('No clips were generated; chapter config is invalid for this source video')
PY
