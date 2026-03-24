#!/bin/bash
set -euo pipefail

VIDEO_FILE=/root/archive-camera.mp4
FRAME_DIR=/root/archive_keyframes
OUTPUT_FILE=/root/frame_hash_index.tsv

mkdir -p "$FRAME_DIR"

ffmpeg -y -i "$VIDEO_FILE" -vf "select='eq(pict_type,I)'" -vsync vfr "$FRAME_DIR/archive_%04d.png"

python3 <<'PY'
import csv
import hashlib
from pathlib import Path

frame_dir = Path("/root/archive_keyframes")
output_file = Path("/root/frame_hash_index.tsv")
frames = sorted(frame_dir.glob("archive_*.png"))

with output_file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(["frame_path", "sequence", "sha256"])
    for sequence, frame_path in enumerate(frames, start=1):
        sha256 = hashlib.sha256(frame_path.read_bytes()).hexdigest()
        writer.writerow([str(frame_path), sequence, sha256])
PY
