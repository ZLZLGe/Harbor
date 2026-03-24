#!/bin/bash
set -euo pipefail

FRAME_DIR=/root/storyboard_frames
VIDEO_FILE=/root/demo-clip.mp4
OUTPUT_CSV=/root/storyboard_manifest.csv

mkdir -p "$FRAME_DIR"

ffmpeg -i "$VIDEO_FILE" -vf "select='eq(pict_type,I)'" -vsync vfr "$FRAME_DIR/scene_%03d.png"

python3 <<'PY'
import csv
from pathlib import Path

from PIL import Image

frame_dir = Path("/root/storyboard_frames")
output_csv = Path("/root/storyboard_manifest.csv")
frames = sorted(frame_dir.glob("scene_*.png"))

with output_csv.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["frame_path", "sequence", "width", "height", "file_size_bytes"])
    for index, frame_path in enumerate(frames, start=1):
        with Image.open(frame_path) as image:
            width, height = image.size
        writer.writerow([
            str(frame_path),
            index,
            width,
            height,
            frame_path.stat().st_size,
        ])
PY
