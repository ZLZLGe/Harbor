#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("/root")
VIDEO_PATH = ROOT / "rooftop_inspection.y4m"
SPEC_PATH = ROOT / "heatmap_spec.json"
OUTPUT_PATH = ROOT / "rooftop_activity_heatmap.npy"

BORDER = 8


def sample_frames(video_path: Path, target_fps: float) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, int(round(source_fps / target_fps)))

    frames = []
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


def warp_with_shift(frame: np.ndarray, dx: float, dy: float) -> np.ndarray:
    matrix = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    h, w = frame.shape[:2]
    return cv2.warpAffine(
        frame,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )


def best_translation(other_gray: np.ndarray, ref_gray: np.ndarray) -> tuple[float, float]:
    shift, _ = cv2.phaseCorrelate(
        other_gray.astype(np.float32),
        ref_gray.astype(np.float32),
    )
    candidates = [shift, (-shift[0], -shift[1]), (0.0, 0.0)]

    best = candidates[0]
    best_error = None
    for dx, dy in candidates:
        aligned = warp_with_shift(other_gray, dx, dy)
        error = float(np.mean(np.abs(ref_gray.astype(np.float32) - aligned.astype(np.float32))))
        if best_error is None or error < best_error:
            best = (dx, dy)
            best_error = error
    return float(best[0]), float(best[1])


def aligned_difference(ref_frame: np.ndarray, other_frame: np.ndarray) -> np.ndarray:
    ref_gray = cv2.cvtColor(ref_frame, cv2.COLOR_BGR2GRAY)
    other_gray = cv2.cvtColor(other_frame, cv2.COLOR_BGR2GRAY)

    dx, dy = best_translation(other_gray, ref_gray)
    aligned = warp_with_shift(other_frame, dx, dy)
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

    gray_diff = cv2.absdiff(ref_gray, aligned_gray).astype(np.float32)
    color_diff = np.linalg.norm(
        ref_frame.astype(np.float32) - aligned.astype(np.float32),
        axis=2,
    )
    return np.maximum(gray_diff, color_diff * 0.65)


def dynamic_mask_for_index(frames: list[np.ndarray], index: int) -> np.ndarray:
    ref_frame = frames[index]
    components = []
    if index > 0:
        components.append(aligned_difference(ref_frame, frames[index - 1]))
    if index + 1 < len(frames):
        components.append(aligned_difference(ref_frame, frames[index + 1]))

    if not components:
        return np.zeros(ref_frame.shape[:2], dtype=bool)

    combined = np.maximum.reduce(components)
    inner = combined[BORDER:-BORDER, BORDER:-BORDER]
    threshold = max(20.0, float(np.percentile(inner, 92)))
    mask = combined >= threshold

    mask[:BORDER, :] = False
    mask[-BORDER:, :] = False
    mask[:, :BORDER] = False
    mask[:, -BORDER:] = False

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    filtered = np.zeros_like(mask, dtype=bool)
    for label in range(1, num_labels):
        if int(stats[label, cv2.CC_STAT_AREA]) >= 18:
            filtered[labels == label] = True
    return filtered


spec = json.loads(SPEC_PATH.read_text())
frames = sample_frames(VIDEO_PATH, float(spec["sample_fps"]))
if not frames:
    raise RuntimeError("No sampled frames were read from the rooftop clip")

expected_shape = tuple(int(v) for v in spec["expected_shape"])
heatmap_counts = np.zeros(expected_shape, dtype=np.float32)

for frame_idx in range(len(frames)):
    mask = dynamic_mask_for_index(frames, frame_idx)
    heatmap_counts += mask.astype(np.float32)

peak = float(heatmap_counts.max())
if peak > 0.0:
    heatmap = heatmap_counts / peak
else:
    heatmap = heatmap_counts

np.save(OUTPUT_PATH, heatmap.astype(np.float32))
PY
