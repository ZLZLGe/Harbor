import csv
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("/root")
OUTPUT_PATH = ROOT / "goalmouth_occupancy.csv"
ROI_PATH = ROOT / "goalmouth_roi.json"
VIDEO_PATH = ROOT / "goalmouth_pan.y4m"

EXPECTED_COLUMNS = [
    "sample_index",
    "timestamp_sec",
    "goal_pixels",
    "occluded_pixels",
    "occlusion_ratio",
]


def polygon_mask(image_size: list[int], polygon: list[list[int]]) -> np.ndarray:
    h, w = int(image_size[0]), int(image_size[1])
    mask = np.zeros((h, w), dtype=np.uint8)
    pts = np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [pts], 1)
    return mask.astype(bool)


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


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


@lru_cache(maxsize=1)
def reference_series() -> tuple[int, list[int], list[float]]:
    roi = json.loads(ROI_PATH.read_text())
    roi_mask = polygon_mask(roi["image_size"], roi["polygon"])
    goal_pixels = int(roi_mask.sum())
    frames = load_sampled_frames(VIDEO_PATH, float(roi["sample_fps"]))

    occluded: list[int] = []
    prev_gray = None
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is None:
            mask = np.zeros_like(gray, dtype=bool)
        else:
            mask = dynamic_mask(prev_gray, gray)
        occluded.append(int(np.logical_and(mask, roi_mask).sum()))
        prev_gray = gray

    ratios = [value / goal_pixels for value in occluded]
    return goal_pixels, occluded, ratios


def test_output_exists():
    assert OUTPUT_PATH.exists(), "Missing /root/goalmouth_occupancy.csv"


def test_header_and_row_count():
    fieldnames, rows = load_rows()
    _, ref_occluded, _ = reference_series()

    assert fieldnames == EXPECTED_COLUMNS, "CSV header does not match the required contract"
    assert len(rows) == len(ref_occluded), "CSV must contain exactly one row per sampled frame"


def test_schema_and_internal_consistency():
    roi = json.loads(ROI_PATH.read_text())
    sample_fps = float(roi["sample_fps"])
    goal_pixels, _, _ = reference_series()
    _, rows = load_rows()

    for expected_index, row in enumerate(rows):
        sample_index = int(row["sample_index"])
        timestamp_sec = float(row["timestamp_sec"])
        goal_value = int(row["goal_pixels"])
        occluded_pixels = int(row["occluded_pixels"])
        ratio = float(row["occlusion_ratio"])

        assert sample_index == expected_index, "sample_index must start at 0 and increase continuously"
        assert abs(timestamp_sec - (sample_index / sample_fps)) <= 1e-6, "timestamp_sec must equal sample_index / sample_fps"
        assert goal_value == goal_pixels, "goal_pixels must equal the polygon area and stay constant"
        assert 0 <= occluded_pixels <= goal_pixels, "occluded_pixels must stay within the polygon area"
        assert 0.0 <= ratio <= 1.0, "occlusion_ratio must stay in [0, 1]"
        assert abs(ratio - (occluded_pixels / goal_pixels)) <= 1e-6, "occlusion_ratio must equal occluded_pixels / goal_pixels"


def test_timeline_matches_reference_semantics():
    _, rows = load_rows()
    _, ref_occluded, ref_ratios = reference_series()

    pred_occluded = np.array([int(row["occluded_pixels"]) for row in rows], dtype=np.float32)
    pred_ratios = np.array([float(row["occlusion_ratio"]) for row in rows], dtype=np.float32)
    ref_occluded_arr = np.array(ref_occluded, dtype=np.float32)
    ref_ratios_arr = np.array(ref_ratios, dtype=np.float32)

    mae_ratio = float(np.mean(np.abs(pred_ratios - ref_ratios_arr)))
    max_ratio_err = float(np.max(np.abs(pred_ratios - ref_ratios_arr)))
    mae_pixels = float(np.mean(np.abs(pred_occluded - ref_occluded_arr)))
    total_ref = float(ref_occluded_arr.sum())
    total_pred = float(pred_occluded.sum())
    total_relative_err = abs(total_pred - total_ref) / max(total_ref, 1.0)

    assert mae_ratio <= 0.08, "Average occupancy ratio error is too large"
    assert max_ratio_err <= 0.18, "Some sampled frames deviate too far from the expected occupancy"
    assert mae_pixels <= 260.0, "Average occluded pixel count drifts too far from the reference"
    assert total_relative_err <= 0.25, "The total amount of predicted goalmouth blockage is too far from the reference"
