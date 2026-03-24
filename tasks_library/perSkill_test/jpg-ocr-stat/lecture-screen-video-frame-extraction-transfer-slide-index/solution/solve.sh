#!/bin/bash

set -euo pipefail

cd /app/workspace

python3 - <<'PY'
import csv
import json
from pathlib import Path

import cv2


workspace = Path("/app/workspace")
config = json.loads((workspace / "lecture_assets" / "lecture_capture_config.json").read_text(encoding="utf-8"))
video_path = workspace / "lecture_assets" / config["video_file"]
preview_dir = workspace / config["preview_dir"]
preview_dir.mkdir(parents=True, exist_ok=True)

slide_x1, slide_y1, slide_x2, slide_y2 = config["slide_region"]
sample_interval_seconds = int(config["sample_interval_seconds"])
change_threshold = float(config["change_threshold"])

cap = cv2.VideoCapture(str(video_path))
if not cap.isOpened():
    raise SystemExit(f"cannot open video: {video_path}")

fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0:
    raise SystemExit("invalid video fps")

frame_interval = max(1, round(fps * sample_interval_seconds))
previous_signature = None
records = []
frame_index = 0
sample_index = 0

while True:
    ok, frame = cap.read()
    if not ok:
        break

    if frame_index % frame_interval == 0:
        crop = frame[slide_y1:slide_y2, slide_x1:slide_x2]
        small = cv2.resize(crop, (180, 100))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        signature = cv2.GaussianBlur(gray, (5, 5), 0)

        if previous_signature is not None:
            mean_diff = float(cv2.absdiff(signature, previous_signature).mean())
            if mean_diff >= change_threshold:
                preview_name = f"change_{len(records) + 1:02d}.jpg"
                preview_rel = f"{config['preview_dir']}/{preview_name}"
                cv2.imwrite(str(workspace / preview_rel), frame)

                seconds = sample_index * sample_interval_seconds
                timestamp = f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
                records.append((timestamp, preview_rel))

        previous_signature = signature
        sample_index += 1

    frame_index += 1

cap.release()

output_path = workspace / "slide_change_index.csv"
with output_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["timestamp", "preview_frame"])
    writer.writerows(records)
PY
