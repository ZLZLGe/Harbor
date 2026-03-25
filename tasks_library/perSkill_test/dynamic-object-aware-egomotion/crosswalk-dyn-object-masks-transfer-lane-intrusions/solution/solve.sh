#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import cv2
import numpy as np

ROI_PATH = Path("/root/ego_lane_roi.json")
VIDEO_PATH = Path("/root/crosswalk_drive.mp4")
OUTPUT_PATH = Path("/root/crosswalk_intrusions.json")

def sample_frame_indices(frame_count: int, native_fps: float, sample_fps: float) -> list[int]:
    indices = []
    sample_idx = 0
    while True:
        frame_idx = int(round(sample_idx * native_fps / sample_fps))
        if frame_idx >= frame_count:
            return indices
        indices.append(frame_idx)
        sample_idx += 1


def load_sampled_grayscale_frames(video_path: Path, sample_fps: float) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    native_fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if native_fps <= 0.0 or frame_count <= 0:
        raise RuntimeError("Video metadata is invalid")

    frames = []
    for frame_idx in sample_frame_indices(frame_count, native_fps, sample_fps):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Failed to read frame {frame_idx}")
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))

    cap.release()
    return frames


def estimate_affine(prev_gray: np.ndarray, curr_gray: np.ndarray) -> np.ndarray:
    points = cv2.goodFeaturesToTrack(
        prev_gray,
        maxCorners=400,
        qualityLevel=0.01,
        minDistance=8,
        blockSize=7,
    )
    if points is None or len(points) < 6:
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    next_points, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, points, None)
    if next_points is None or status is None:
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    good_prev = points[status.reshape(-1) == 1].reshape(-1, 2)
    good_curr = next_points[status.reshape(-1) == 1].reshape(-1, 2)
    if len(good_prev) < 6:
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    matrix, _ = cv2.estimateAffinePartial2D(
        good_prev,
        good_curr,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
        maxIters=2000,
        confidence=0.99,
    )
    if matrix is None:
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    return matrix.astype(np.float32)


def dynamic_masks(frames: list[np.ndarray]) -> list[np.ndarray]:
    if not frames:
        return []

    h, w = frames[0].shape
    min_area = max(400, int(round(0.002 * h * w)))
    open_kernel = np.ones((3, 3), dtype=np.uint8)
    close_kernel = np.ones((7, 7), dtype=np.uint8)
    masks = [np.zeros((h, w), dtype=bool)]

    for prev_gray, curr_gray in zip(frames, frames[1:]):
        matrix = estimate_affine(prev_gray, curr_gray)
        warped_prev = cv2.warpAffine(
            prev_gray,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        valid = cv2.warpAffine(
            np.ones((h, w), dtype=np.uint8),
            matrix,
            (w, h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        ).astype(bool)

        diff = cv2.absdiff(curr_gray, warped_prev)
        values = diff[valid]
        if values.size == 0:
            masks.append(np.zeros((h, w), dtype=bool))
            continue

        median = float(np.median(values))
        mad = float(np.median(np.abs(values.astype(np.float32) - median)))
        threshold = max(20.0, median + 3.0 * 1.4826 * mad)

        raw = np.logical_and(diff > threshold, valid).astype(np.uint8) * 255
        cleaned = cv2.morphologyEx(raw, cv2.MORPH_OPEN, open_kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        mask = np.zeros((h, w), dtype=bool)
        for component_id in range(1, num_labels):
            if int(stats[component_id, cv2.CC_STAT_AREA]) >= min_area:
                mask |= labels == component_id
        masks.append(mask)

    return masks


def polygon_mask(image_size: list[int], polygon: list[list[int]]) -> np.ndarray:
    h, w = int(image_size[0]), int(image_size[1])
    mask = np.zeros((h, w), dtype=np.uint8)
    points = np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [points], 1)
    return mask.astype(bool)


def merge_windows(active: list[bool]) -> list[dict[str, int]]:
    windows = []
    start = None
    for idx, flag in enumerate(active):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            windows.append({"start_frame": start, "end_frame": idx})
            start = None
    if start is not None:
        windows.append({"start_frame": start, "end_frame": len(active)})
    return windows


config = json.loads(ROI_PATH.read_text())
frames = load_sampled_grayscale_frames(VIDEO_PATH, float(config["sample_fps"]))
masks = dynamic_masks(frames)
lane_mask = polygon_mask(config["image_size"], config["polygon"])
threshold = int(config["intrusion_min_pixels"])
active = [int(np.logical_and(mask, lane_mask).sum()) >= threshold for mask in masks]

OUTPUT_PATH.write_text(
    json.dumps(
        {
            "sample_fps": float(config["sample_fps"]),
            "windows": merge_windows(active),
        },
        indent=2,
    )
)
PY
