#!/bin/bash
set -euo pipefail

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:00.000 -t 00:00:04.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /root/transfer2_part_1.mp4

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:04.000 -t 00:00:04.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /root/transfer2_part_2.mp4

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:08.000 -t 00:00:04.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /root/transfer2_part_3.mp4

python3 - <<'PY'
import json
import re
import subprocess

parts = [
    ("/root/transfer2_part_1.mp4", 0.0),
    ("/root/transfer2_part_2.mp4", 4.0),
    ("/root/transfer2_part_3.mp4", 8.0),
]


def dur(path: str) -> float:
    res = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+))", res.stderr)
    if not m:
        raise RuntimeError(f"Cannot parse duration for {path}")
    hh, mm, ss = m.groups()
    return int(hh) * 3600 + int(mm) * 60 + float(ss)

result = {
    "input_file": "/root/input.mp4",
    "parts": [
        {
            "file": file,
            "start_sec": start,
            "duration_sec": dur(file),
        }
        for file, start in parts
    ],
}

with open("/root/transfer2_split_map.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
PY
