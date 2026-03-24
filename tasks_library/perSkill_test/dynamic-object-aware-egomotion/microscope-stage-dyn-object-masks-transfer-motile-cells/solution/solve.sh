#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

import cv2
import numpy as np

INPUT_PATH = Path("/root/microscope_stage_drift.mp4")
OUTPUT_PATH = Path("/root/motile_cells_dyn_masks.npz")
TARGET_FPS = 4.0
MIN_THRESHOLD = 12.0
MIN_AREA = 55
EDGE_MARGIN = 10


def sample_frames(video_path: Path, target_fps: float) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or target_fps
    stride = max(1, int(round(source_fps / target_fps)))

    frames: list[np.ndarray] = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % stride == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        frame_idx += 1

    cap.release()
    if not frames:
        raise RuntimeError("No sampled frames were extracted")
    return frames


def estimate_translation(prev_gray: np.ndarray, curr_gray: np.ndarray) -> tuple[float, float]:
    prev32 = prev_gray.astype(np.float32)
    curr32 = curr_gray.astype(np.float32)
    window = cv2.createHanningWindow((prev_gray.shape[1], prev_gray.shape[0]), cv2.CV_32F)
    shift, _ = cv2.phaseCorrelate(prev32 * window, curr32 * window)
    return float(shift[0]), float(shift[1])


def warp_image(image: np.ndarray, dx: float, dy: float, interpolation: int) -> np.ndarray:
    matrix = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    return cv2.warpAffine(
        image,
        matrix,
        (image.shape[1], image.shape[0]),
        flags=interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def detect_mask(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray,
    prev_mask: np.ndarray | None,
) -> tuple[np.ndarray, tuple[float, float]]:
    dx, dy = estimate_translation(prev_gray, curr_gray)

    prev_blur = cv2.GaussianBlur(prev_gray, (0, 0), 1.2)
    curr_blur = cv2.GaussianBlur(curr_gray, (0, 0), 1.2)

    def segment_cells(gray: np.ndarray) -> np.ndarray:
        smooth = cv2.GaussianBlur(gray, (0, 0), 1.2)
        local_bg = cv2.GaussianBlur(smooth, (0, 0), 10.0)
        dark = (smooth.astype(np.float32) + 4.0 < local_bg.astype(np.float32)).astype(np.uint8) * 255
        dark = cv2.morphologyEx(
            dark,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        )
        dark = cv2.morphologyEx(
            dark,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        )

        count, labels, stats, _ = cv2.connectedComponentsWithStats((dark > 0).astype(np.uint8), connectivity=8)
        mask = np.zeros_like(gray, dtype=bool)
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if 35 <= area <= 2200:
                mask |= labels == label
        return mask

    warped_prev = warp_image(prev_blur, dx, dy, cv2.INTER_LINEAR)
    valid = warp_image(np.ones_like(prev_gray, dtype=np.uint8), dx, dy, cv2.INTER_NEAREST) > 0
    if EDGE_MARGIN > 0:
        valid[:EDGE_MARGIN, :] = False
        valid[-EDGE_MARGIN:, :] = False
        valid[:, :EDGE_MARGIN] = False
        valid[:, -EDGE_MARGIN:] = False

    diff = cv2.absdiff(curr_blur, warped_prev).astype(np.float32)
    values = diff[valid]
    if values.size == 0:
        return np.zeros_like(curr_gray, dtype=bool), (dx, dy)

    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    threshold = max(MIN_THRESHOLD, median + 3.0 * 1.4826 * mad)
    raw = (diff > threshold) & valid

    opened = cv2.morphologyEx(
        raw.astype(np.uint8) * 255,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    closed = cv2.morphologyEx(
        opened,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
    )
    dilated = cv2.dilate(
        closed,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )
    filled = cv2.morphologyEx(
        dilated,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)),
    )

    if prev_mask is not None:
        warped_prev_mask = warp_image(prev_mask.astype(np.uint8) * 255, dx, dy, cv2.INTER_NEAREST) > 0
        support = (diff > threshold * 0.72) & valid
        filled = np.logical_or(filled > 0, np.logical_and(warped_prev_mask, support)).astype(np.uint8) * 255

    motion_seed = filled > 0
    curr_cells = segment_cells(curr_gray) & valid
    prev_cells = segment_cells(prev_gray)
    warped_prev_cells = warp_image(prev_cells.astype(np.uint8) * 255, dx, dy, cv2.INTER_NEAREST) > 0

    seed_support = cv2.dilate(
        motion_seed.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=1,
    ) > 0

    count, labels, stats, _ = cv2.connectedComponentsWithStats(curr_cells.astype(np.uint8), connectivity=8)
    mask = np.zeros_like(curr_gray, dtype=bool)
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < MIN_AREA or area > 2200:
            continue
        component = labels == label
        overlap_pixels = int(np.logical_and(component, warped_prev_cells).sum())
        overlap_ratio = overlap_pixels / area
        seed_pixels = int(np.logical_and(component, seed_support).sum())
        change_pixels = int(np.logical_and(component, np.logical_or(motion_seed, ~warped_prev_cells)).sum())
        if overlap_pixels < 18:
            mask |= component
            continue
        if overlap_ratio < 0.58:
            mask |= component
            continue
        if seed_pixels >= max(10, int(area * 0.08)) and change_pixels >= max(12, int(area * 0.16)):
            mask |= component

    if not mask.any():
        count, labels, stats, _ = cv2.connectedComponentsWithStats(np.logical_and(curr_cells, seed_support).astype(np.uint8), connectivity=8)
        for label in range(1, count):
            if int(stats[label, cv2.CC_STAT_AREA]) >= MIN_AREA:
                mask |= labels == label

    return mask, (dx, dy)


def encode_masks(masks: list[np.ndarray]) -> dict[str, np.ndarray]:
    h, w = masks[0].shape
    encoded: dict[str, np.ndarray] = {"shape": np.array([h, w], dtype=np.int32)}
    for i, mask in enumerate(masks):
        rows, cols = np.nonzero(mask)
        counts = np.bincount(rows, minlength=h)
        indptr = np.concatenate([[0], np.cumsum(counts, dtype=np.int32)])
        encoded[f"f_{i}_data"] = np.ones(len(rows), dtype=np.uint8)
        encoded[f"f_{i}_indices"] = cols.astype(np.int32)
        encoded[f"f_{i}_indptr"] = indptr.astype(np.int32)
    return encoded


frames = sample_frames(INPUT_PATH, TARGET_FPS)
masks: list[np.ndarray] = [np.zeros_like(frames[0], dtype=bool)]
prev_mask: np.ndarray | None = None

for i in range(1, len(frames)):
    mask, _ = detect_mask(frames[i - 1], frames[i], prev_mask)
    masks.append(mask)
    prev_mask = mask

if len(masks) > 1:
    masks[0] = masks[1].copy()

np.savez_compressed(OUTPUT_PATH, **encode_masks(masks))
PY
