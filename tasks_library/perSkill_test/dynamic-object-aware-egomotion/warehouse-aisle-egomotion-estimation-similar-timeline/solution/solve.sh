#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

MANIFEST_PATH = Path("/root/run_manifest.json")

VALID_LABELS = [
    "Stay",
    "Dolly In",
    "Dolly Out",
    "Pan Left",
    "Pan Right",
    "Tilt Up",
    "Tilt Down",
    "Roll Left",
    "Roll Right",
]


def load_manifest():
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def sample_frames(video_path: str, target_fps: float):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or target_fps
    stride = max(1, int(fps / target_fps))

    frames = []
    frame_id = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_id % stride == 0:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        frame_id += 1

    cap.release()
    return frames


def estimate_motion(prev_gray: np.ndarray, curr_gray: np.ndarray):
    points = cv2.goodFeaturesToTrack(
        prev_gray,
        maxCorners=400,
        qualityLevel=0.01,
        minDistance=8,
        blockSize=7,
    )
    if points is None or len(points) < 12:
        return None

    next_points, status, _ = cv2.calcOpticalFlowPyrLK(
        prev_gray,
        curr_gray,
        points,
        None,
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    if next_points is None or status is None:
        return None

    good_prev = points[status.flatten() == 1]
    good_next = next_points[status.flatten() == 1]
    if len(good_prev) < 12:
        return None

    affine, _ = cv2.estimateAffinePartial2D(
        good_prev,
        good_next,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
        maxIters=2000,
        confidence=0.99,
    )
    return affine


def classify_motion(affine: np.ndarray | None, width: int, height: int):
    if affine is None:
        return ["Stay"]

    a, b, tx = affine[0]
    c, d, ty = affine[1]

    scale_x = math.sqrt(a * a + c * c)
    scale_y = math.sqrt(b * b + d * d)
    scale = (scale_x + scale_y) / 2.0
    rotation = math.atan2(c, a)

    labels = []
    if abs(scale - 1.0) > 0.01:
        labels.append("Dolly In" if scale > 1.0 else "Dolly Out")

    if abs(tx) > width * 0.02:
        labels.append("Pan Left" if tx > 0 else "Pan Right")

    if abs(ty) > height * 0.03:
        labels.append("Tilt Up" if ty > 0 else "Tilt Down")

    if abs(rotation) > math.radians(1.5):
        labels.append("Roll Right" if rotation > 0 else "Roll Left")

    if not labels:
        return ["Stay"]

    ordered = [label for label in VALID_LABELS if label in labels]
    return ordered


def smooth_labels(frame_labels: list[list[str]], window: int = 3):
    smoothed = []
    for idx in range(len(frame_labels)):
        start = max(0, idx - window // 2)
        end = min(len(frame_labels), idx + window // 2 + 1)
        counts = Counter()
        for pos in range(start, end):
            counts.update(frame_labels[pos])

        picked = [label for label in VALID_LABELS if counts[label] >= (end - start) / 2]
        smoothed.append(picked or ["Stay"])
    return smoothed


def merge_intervals(frame_labels: list[list[str]]):
    if not frame_labels:
        return {}

    merged = {}
    start = 0
    prev = tuple(frame_labels[0])

    for idx in range(1, len(frame_labels)):
        current = tuple(frame_labels[idx])
        if current != prev:
            merged[f"{start}->{idx}"] = list(prev)
            start = idx
            prev = current

    merged[f"{start}->{len(frame_labels)}"] = list(prev)
    return merged


def main():
    cv2.setRNGSeed(0)
    manifest = load_manifest()
    frames = sample_frames(manifest["video_path"], manifest["sample_fps"])
    if len(frames) < 2:
        raise RuntimeError("not enough sampled frames")

    height, width = frames[0].shape
    raw_labels = []
    for idx in range(len(frames) - 1):
        affine = estimate_motion(frames[idx], frames[idx + 1])
        raw_labels.append(classify_motion(affine, width, height))

    timeline = merge_intervals(smooth_labels(raw_labels))
    with Path(manifest["output_path"]).open("w") as f:
        json.dump(timeline, f, indent=2)


if __name__ == "__main__":
    main()
PY
