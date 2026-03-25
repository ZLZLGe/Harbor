import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("/root")
OUTPUT_PATH = ROOT / "crosswalk_intrusions.json"
ROI_PATH = ROOT / "ego_lane_roi.json"
VIDEO_PATH = ROOT / "crosswalk_drive.mp4"


def load_output() -> dict:
    return json.loads(OUTPUT_PATH.read_text())


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
    assert cap.isOpened(), f"Failed to open {video_path}"

    native_fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert native_fps > 0.0 and frame_count > 0, "Video metadata is invalid"

    frames = []
    for frame_idx in sample_frame_indices(frame_count, native_fps, sample_fps):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        assert ok, f"Failed to read frame {frame_idx}"
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
    pts = np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [pts], 1)
    return mask.astype(bool)


def expand_windows(windows: list[dict], frame_count: int) -> np.ndarray:
    active = np.zeros(frame_count, dtype=bool)
    for window in windows:
        active[int(window["start_frame"]) : int(window["end_frame"])] = True
    return active


def reference_active_frames() -> np.ndarray:
    roi = json.loads(ROI_PATH.read_text())
    frames = load_sampled_grayscale_frames(VIDEO_PATH, float(roi["sample_fps"]))
    masks = dynamic_masks(frames)
    lane_mask = polygon_mask(roi["image_size"], roi["polygon"])
    threshold = int(roi["intrusion_min_pixels"])
    return np.array(
        [int(np.logical_and(mask, lane_mask).sum()) >= threshold for mask in masks],
        dtype=bool,
    )


def merge_windows(active: np.ndarray) -> list[dict[str, int]]:
    windows = []
    start = None
    for idx, flag in enumerate(active.tolist()):
        if flag and start is None:
            start = idx
        if not flag and start is not None:
            windows.append({"start_frame": start, "end_frame": idx})
            start = None
    if start is not None:
        windows.append({"start_frame": start, "end_frame": len(active)})
    return windows


def test_output_exists():
    assert OUTPUT_PATH.exists(), "Missing /root/crosswalk_intrusions.json"


def test_schema_and_ordering():
    payload = load_output()
    roi = json.loads(ROI_PATH.read_text())

    assert isinstance(payload, dict), "Output root must be a JSON object"
    assert "sample_fps" in payload, "Missing sample_fps"
    assert "windows" in payload, "Missing windows"
    assert float(payload["sample_fps"]) == float(roi["sample_fps"]), "sample_fps must match ROI config"
    assert isinstance(payload["windows"], list), "windows must be a list"

    prev_end = 0
    for idx, window in enumerate(payload["windows"]):
        assert isinstance(window, dict), f"windows[{idx}] must be an object"
        assert "start_frame" in window and "end_frame" in window, f"windows[{idx}] must contain start_frame and end_frame"
        assert isinstance(window["start_frame"], int), f"windows[{idx}].start_frame must be an integer"
        assert isinstance(window["end_frame"], int), f"windows[{idx}].end_frame must be an integer"
        assert 0 <= window["start_frame"] < window["end_frame"], f"windows[{idx}] has invalid frame bounds"
        assert window["start_frame"] >= prev_end, f"windows[{idx}] must be sorted and non-overlapping"
        prev_end = window["end_frame"]


def test_intrusion_windows_match_public_video_semantics():
    payload = load_output()
    expected = reference_active_frames()
    predicted = expand_windows(payload["windows"], len(expected))
    assert np.array_equal(
        predicted,
        expected,
    ), "Predicted intrusion frames must match the published video-processing rules on the sampled frames"


def test_contiguous_intrusion_frames_are_merged_into_single_windows():
    payload = load_output()
    expected_windows = merge_windows(reference_active_frames())
    assert payload["windows"] == expected_windows, (
        "Each maximal contiguous run of intrusion frames must appear as exactly one window; "
        "do not split one continuous run into adjacent sub-windows"
    )
