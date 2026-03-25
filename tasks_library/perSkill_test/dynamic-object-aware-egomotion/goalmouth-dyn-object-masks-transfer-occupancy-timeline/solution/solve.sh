#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
from pathlib import Path

import cv2
import numpy as np

VIDEO_PATH = Path("/root/goalmouth_pan.y4m")
ROI_PATH = Path("/root/goalmouth_roi.json")
OUTPUT_PATH = Path("/root/goalmouth_occupancy.csv")


def load_sampled_frames(video_path: Path, sample_fps: float) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        raise RuntimeError("invalid video fps")

    step = max(1, int(round(video_fps / sample_fps)))
    frames: list[np.ndarray] = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % step == 0:
            frames.append(frame)
        frame_idx += 1
    cap.release()
    return frames


def polygon_mask(image_size: list[int], polygon: list[list[int]]) -> np.ndarray:
    h, w = int(image_size[0]), int(image_size[1])
    mask = np.zeros((h, w), dtype=np.uint8)
    pts = np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [pts], 1)
    return mask.astype(bool)


def estimate_warp(prev_gray: np.ndarray, curr_gray: np.ndarray) -> np.ndarray:
    pts = cv2.goodFeaturesToTrack(
        prev_gray,
        maxCorners=300,
        qualityLevel=0.01,
        minDistance=7,
        blockSize=7,
    )
    if pts is not None and len(pts) >= 6:
        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, pts, None)
        if next_pts is not None and status is not None:
            good_prev = pts[status.ravel() == 1]
            good_curr = next_pts[status.ravel() == 1]
            if len(good_prev) >= 6:
                affine, _ = cv2.estimateAffinePartial2D(
                    good_prev,
                    good_curr,
                    method=cv2.RANSAC,
                    ransacReprojThreshold=3.0,
                )
                if affine is not None:
                    return affine.astype(np.float32)

    shift, _ = cv2.phaseCorrelate(prev_gray.astype(np.float32), curr_gray.astype(np.float32))
    dx, dy = shift
    return np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)


def dynamic_mask(prev_gray: np.ndarray, curr_gray: np.ndarray) -> np.ndarray:
    h, w = curr_gray.shape
    warp = estimate_warp(prev_gray, curr_gray)
    warped_prev = cv2.warpAffine(
        prev_gray,
        warp,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    valid = cv2.warpAffine(
        np.ones((h, w), dtype=np.uint8),
        warp,
        (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    ).astype(bool)

    diff = cv2.absdiff(curr_gray, warped_prev)
    values = diff[valid]
    if values.size == 0:
        return np.zeros((h, w), dtype=bool)

    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    threshold = max(18.0, median + 3.0 * 1.4826 * mad)
    raw = np.logical_and(diff > threshold, valid)

    opened = cv2.morphologyEx(raw.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    binary = (closed > 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    min_area = max(30, int(h * w * 0.0012))
    mask = np.zeros((h, w), dtype=bool)
    for label_id in range(1, count):
        if int(stats[label_id, cv2.CC_STAT_AREA]) >= min_area:
            mask |= labels == label_id
    return mask


def main() -> None:
    roi = json.loads(ROI_PATH.read_text())
    sample_fps = float(roi["sample_fps"])
    frames = load_sampled_frames(VIDEO_PATH, sample_fps)
    roi_mask = polygon_mask(roi["image_size"], roi["polygon"])
    goal_pixels = int(roi_mask.sum())

    rows: list[dict[str, str | int | float]] = []
    prev_gray = None
    for sample_index, frame in enumerate(frames):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is None:
            mask = np.zeros_like(gray, dtype=bool)
        else:
            mask = dynamic_mask(prev_gray, gray)
        occluded_pixels = int(np.logical_and(mask, roi_mask).sum())
        ratio = occluded_pixels / goal_pixels if goal_pixels else 0.0
        rows.append(
            {
                "sample_index": sample_index,
                "timestamp_sec": f"{sample_index / sample_fps:.6f}",
                "goal_pixels": goal_pixels,
                "occluded_pixels": occluded_pixels,
                "occlusion_ratio": f"{ratio:.6f}",
            }
        )
        prev_gray = gray

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_index",
                "timestamp_sec",
                "goal_pixels",
                "occluded_pixels",
                "occlusion_ratio",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
PY
