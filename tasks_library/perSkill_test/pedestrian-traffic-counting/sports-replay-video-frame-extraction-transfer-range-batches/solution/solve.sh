#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from pathlib import Path

import cv2

INPUT_ROOT = Path("/app/input")
VIDEOS_ROOT = INPUT_ROOT / "videos"
CONFIG_PATH = INPUT_ROOT / "replay_ranges.csv"
OUTPUT_ROOT = Path("/app/output")
BATCH_ROOT = OUTPUT_ROOT / "replay_batches"
SUMMARY_PATH = OUTPUT_ROOT / "replay_range_summary.csv"

BATCH_ROOT.mkdir(parents=True, exist_ok=True)

with CONFIG_PATH.open("r", encoding="utf-8", newline="") as fh:
    clips = list(csv.DictReader(fh))

summary_rows = []

for clip in clips:
    clip_id = clip["clip_id"]
    source_video = clip["source_video"]
    start_frame = int(clip["start_frame"])
    end_frame = int(clip["end_frame"])

    video_path = VIDEOS_ROOT / source_video
    output_dir = BATCH_ROOT / clip_id
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    written = 0
    for frame_index in range(start_frame, end_frame + 1):
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"视频在读取到帧 {frame_index} 前提前结束: {video_path}")
        frame_path = output_dir / f"frame_{frame_index:06d}.png"
        if not cv2.imwrite(str(frame_path), frame):
            raise RuntimeError(f"写入 PNG 失败: {frame_path}")
        written += 1

    cap.release()

    summary_rows.append(
        {
            "clip_id": clip_id,
            "source_video": source_video,
            "start_frame": str(start_frame),
            "end_frame": str(end_frame),
            "frames_written": str(written),
            "output_dir": f"replay_batches/{clip_id}",
        }
    )

with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "clip_id",
            "source_video",
            "start_frame",
            "end_frame",
            "frames_written",
            "output_dir",
        ],
    )
    writer.writeheader()
    writer.writerows(summary_rows)
PY
