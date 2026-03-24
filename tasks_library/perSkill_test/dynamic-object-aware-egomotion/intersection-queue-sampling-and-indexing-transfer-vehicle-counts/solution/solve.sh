#!/bin/bash
set -e

python3 <<'PY'
import csv
from pathlib import Path

import cv2
import numpy as np

VIDEO_PATH = Path("/root/input.mp4")
OUTPUT_PATH = Path("/root/pred_queue_counts.csv")

TARGET_FPS = 3.0
QUEUE_TOP = 10
QUEUE_BOTTOM = 166
QUEUE_LEFT = 146
QUEUE_RIGHT = 214
MIN_AREA = 320


def sample_frames(video_path: Path, target_fps: float) -> tuple[list[int], list[np.ndarray]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(source_fps / target_fps)))

    sample_ids = list(range(0, total_frames, step))
    frames = []
    for frame_id in sample_ids:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"failed to read frame {frame_id}")
        frames.append(frame)

    cap.release()
    return sample_ids, frames


def count_queued_vehicles(frame: np.ndarray) -> int:
    roi = frame[QUEUE_TOP:QUEUE_BOTTOM, QUEUE_LEFT:QUEUE_RIGHT]
    blue = roi[:, :, 0]
    green = roi[:, :, 1]
    red = roi[:, :, 2]

    mask = (red >= 170) & (green >= 110) & (green <= 220) & (blue <= 120)
    mask = mask.astype(np.uint8)

    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    count = 0
    for label_id in range(1, num_labels):
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area >= MIN_AREA:
            count += 1
    return count


sample_ids, sampled_frames = sample_frames(VIDEO_PATH, TARGET_FPS)

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sample_index", "source_frame_id", "queued_vehicle_count"])
    for sample_index, (frame_id, frame) in enumerate(zip(sample_ids, sampled_frames)):
        writer.writerow([sample_index, frame_id, count_queued_vehicles(frame)])
PY
