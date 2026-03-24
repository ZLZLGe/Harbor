#!/bin/bash
set -e

python3 <<'PY'
import json
from pathlib import Path

import cv2
import numpy as np

VIDEO_PATH = Path("/root/input.mp4")
OUTPUT_PATH = Path("/root/pred_line_state_spans.json")

TARGET_FPS = 5.0
BELT_TOP = 74
BELT_BOTTOM = 142


def sample_frames(video_path: Path, target_fps: float) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(source_fps / target_fps)))

    frames = []
    for frame_id in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"failed to read frame {frame_id}")
        frames.append(frame)

    cap.release()
    return frames


def extract_package_mask(frame: np.ndarray) -> np.ndarray:
    roi = frame[BELT_TOP:BELT_BOTTOM]
    blue = roi[:, :, 0]
    green = roi[:, :, 1]
    red = roi[:, :, 2]

    mask = (red >= 180) & (green >= 110) & (green <= 210) & (blue <= 120)
    mask = mask.astype(np.uint8)

    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask.astype(bool)


def classify_state(mask: np.ndarray) -> str:
    coverage = float(mask.mean())
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    large_components = 0
    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] >= 60:
            large_components += 1

    if coverage < 0.01:
        return "Empty"
    if coverage > 0.11 or large_components >= 6:
        return "Backlog"
    return "Flowing"


def merge_labels(labels: list[str]) -> dict[str, list[str]]:
    spans: dict[str, list[str]] = {}
    start = 0
    current = labels[0]
    for idx in range(1, len(labels)):
        if labels[idx] != current:
            spans[f"{start}->{idx}"] = [current]
            start = idx
            current = labels[idx]
    spans[f"{start}->{len(labels)}"] = [current]
    return spans


sampled_frames = sample_frames(VIDEO_PATH, TARGET_FPS)
labels = [classify_state(extract_package_mask(frame)) for frame in sampled_frames]
spans = merge_labels(labels)

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(spans, f, indent=2)
PY
