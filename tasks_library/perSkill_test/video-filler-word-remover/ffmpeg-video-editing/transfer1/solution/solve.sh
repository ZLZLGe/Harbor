#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

source = Path('/root/transfer1_source.mp4')
windows_path = Path('/root/data/transfer1_remove_windows.json')
output_video = Path('/root/transfer1_clean_cut.mp4')
report_path = Path('/root/transfer1_redaction_report.json')


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def merge_windows(rows: list[dict], duration: float) -> list[tuple[float, float]]:
    clipped = []
    for row in rows:
        start = max(0.0, float(row['start']))
        end = min(duration, float(row['end']))
        if end > start:
            clipped.append((start, end))
    clipped.sort()
    merged: list[tuple[float, float]] = []
    for start, end in clipped:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


duration = ffprobe_duration(source)
raw = json.loads(windows_path.read_text(encoding='utf-8'))
removed = merge_windows(raw, duration)

keep: list[tuple[float, float]] = []
cursor = 0.0
for start, end in removed:
    if start > cursor:
        keep.append((cursor, start))
    cursor = max(cursor, end)
if cursor < duration:
    keep.append((cursor, duration))

work = Path('/tmp/transfer1_segments')
work.mkdir(parents=True, exist_ok=True)
keep_files = []
for idx, (start, end) in enumerate(keep, start=1):
    seg_path = work / f'keep_{idx:03d}.mp4'
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
    keep_files.append(seg_path)

list_path = work / 'keep_segments.txt'
with list_path.open('w', encoding='utf-8') as handle:
    for seg in keep_files:
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

removed_total = sum(end - start for start, end in removed)
kept_total = sum(end - start for start, end in keep)

report = {
    'source_video': source.name,
    'output_video': output_video.name,
    'source_duration_seconds': round(duration, 3),
    'removed_windows_merged': [{'start': round(a, 3), 'end': round(b, 3)} for a, b in removed],
    'keep_windows': [{'start': round(a, 3), 'end': round(b, 3)} for a, b in keep],
    'removed_total_seconds': round(removed_total, 3),
    'kept_total_seconds': round(kept_total, 3),
}
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
PY
