import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")
ANNOTATION_PATH = ROOT / "atrium_annotations.json"
INTERVAL_PATH = ROOT / "pred_camera_intervals.json"
MASK_PATH = ROOT / "pred_crowd_masks.npz"

VALID_LABELS = {
    "Stay",
    "Dolly In",
    "Dolly Out",
    "Pan Left",
    "Pan Right",
    "Tilt Up",
    "Tilt Down",
    "Roll Left",
    "Roll Right",
}


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def load_sparse_masks(path: Path) -> tuple[tuple[int, int], list[np.ndarray]]:
    data = np.load(path)
    shape = tuple(int(v) for v in data["shape"])
    masks = []
    index = 0
    while f"f_{index}_data" in data:
        indices = data[f"f_{index}_indices"]
        indptr = data[f"f_{index}_indptr"]
        mask = np.zeros(shape, dtype=bool)
        for row in range(len(indptr) - 1):
            start = int(indptr[row])
            end = int(indptr[row + 1])
            cols = indices[start:end]
            if len(cols) > 0:
                mask[row, cols] = True
        masks.append(mask)
        index += 1
    return shape, masks


def find_segment(segments: list[dict], frame_id: int) -> dict:
    for segment in segments:
        if segment["start_frame"] <= frame_id < segment["end_frame"]:
            return segment
    raise AssertionError(f"source frame {frame_id} is not covered")


def expected_outputs() -> tuple[dict[str, list[str]], list[np.ndarray], tuple[int, int], int]:
    annotations = load_json(ANNOTATION_PATH)
    sample_source_frames = annotations["video"]["sample_source_frames"]
    shape = (annotations["video"]["height"], annotations["video"]["width"])

    frame_labels = []
    for frame_id in sample_source_frames:
        segment = find_segment(annotations["camera_segments"], frame_id)
        frame_labels.append(sorted(segment["labels"]))

    intervals: dict[str, list[str]] = {}
    start = 0
    current = tuple(frame_labels[0])
    for index in range(1, len(frame_labels)):
        candidate = tuple(frame_labels[index])
        if candidate != current:
            intervals[f"{start}->{index}"] = list(current)
            start = index
            current = candidate
    intervals[f"{start}->{len(frame_labels)}"] = list(current)

    masks = []
    for frame_id in sample_source_frames:
        segment = find_segment(annotations["crowd_segments"], frame_id)
        mask = np.zeros(shape, dtype=bool)
        for x0, y0, x1, y1 in segment["boxes"]:
            mask[y0:y1, x0:x1] = True
        masks.append(mask)

    return intervals, masks, shape, len(sample_source_frames)


def canonicalize_intervals(intervals: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized = {}
    for key, labels in intervals.items():
        normalized[key] = sorted(labels)
    return normalized


def test_output_files_exist():
    assert INTERVAL_PATH.exists(), "Missing /root/pred_camera_intervals.json"
    assert MASK_PATH.exists(), "Missing /root/pred_crowd_masks.npz"


def test_camera_interval_schema_and_coverage():
    _, _, _, sample_count = expected_outputs()
    pred = load_json(INTERVAL_PATH)

    assert isinstance(pred, dict)
    ordered = []
    for key, labels in pred.items():
        assert "->" in key, f"Invalid interval key: {key}"
        start_str, end_str = key.split("->")
        assert start_str.isdigit() and end_str.isdigit(), f"Non-integer interval key: {key}"
        start = int(start_str)
        end = int(end_str)
        assert 0 <= start < end <= sample_count, f"Out-of-range interval key: {key}"
        assert isinstance(labels, list) and labels, f"Labels must be a non-empty list: {key}"
        for label in labels:
            assert label in VALID_LABELS, f"Invalid label: {label}"
        ordered.append((start, end))

    ordered.sort()
    assert ordered[0][0] == 0, "Intervals must start at sample index 0"
    for previous, current in zip(ordered, ordered[1:]):
        assert previous[1] == current[0], "Intervals must be contiguous without gaps"
    assert ordered[-1][1] == sample_count, "Intervals must cover all sampled frames"


def test_camera_intervals_match_expected_projection():
    expected, _, _, _ = expected_outputs()
    pred = load_json(INTERVAL_PATH)
    assert canonicalize_intervals(pred) == canonicalize_intervals(expected)


def test_crowd_masks_match_expected_projection():
    _, expected_masks, expected_shape, sample_count = expected_outputs()
    shape, pred_masks = load_sparse_masks(MASK_PATH)

    assert shape == expected_shape
    assert len(pred_masks) == sample_count

    for index, (pred_mask, expected_mask) in enumerate(zip(pred_masks, expected_masks)):
        assert np.array_equal(pred_mask, expected_mask), f"Mask mismatch at sampled frame {index}"
