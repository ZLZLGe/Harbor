#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")
ANNOTATION_PATH = ROOT / "atrium_annotations.json"
INTERVAL_OUTPUT = ROOT / "pred_camera_intervals.json"
MASK_OUTPUT = ROOT / "pred_crowd_masks.npz"


def load_annotations(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def find_segment(segments: list[dict], frame_id: int, field: str) -> dict:
    for segment in segments:
        if segment["start_frame"] <= frame_id < segment["end_frame"]:
            return segment
    raise ValueError(f"source frame {frame_id} not covered by {field}")


def build_frame_labels(sample_source_frames: list[int], camera_segments: list[dict]) -> list[list[str]]:
    frame_labels = []
    for frame_id in sample_source_frames:
        segment = find_segment(camera_segments, frame_id, "camera_segments")
        frame_labels.append(sorted(segment["labels"]))
    return frame_labels


def merge_intervals(frame_labels: list[list[str]]) -> dict[str, list[str]]:
    if not frame_labels:
        return {}

    merged: dict[str, list[str]] = {}
    start = 0
    current = tuple(frame_labels[0])

    for idx in range(1, len(frame_labels)):
        candidate = tuple(frame_labels[idx])
        if candidate != current:
            merged[f"{start}->{idx}"] = list(current)
            start = idx
            current = candidate

    merged[f"{start}->{len(frame_labels)}"] = list(current)
    return merged


def rasterize_boxes(boxes: list[list[int]], shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = True
    return mask


def build_masks(sample_source_frames: list[int], crowd_segments: list[dict], shape: tuple[int, int]) -> list[np.ndarray]:
    masks = []
    for frame_id in sample_source_frames:
        segment = find_segment(crowd_segments, frame_id, "crowd_segments")
        masks.append(rasterize_boxes(segment["boxes"], shape))
    return masks


def save_sparse_masks(masks: list[np.ndarray], shape: tuple[int, int], output_path: Path) -> None:
    save_dict: dict[str, np.ndarray] = {"shape": np.array(shape, dtype=np.int32)}

    for index, mask in enumerate(masks):
        indices: list[int] = []
        indptr = [0]
        for row in mask:
            row_indices = np.flatnonzero(row)
            indices.extend(row_indices.tolist())
            indptr.append(len(indices))

        save_dict[f"f_{index}_data"] = np.ones(len(indices), dtype=bool)
        save_dict[f"f_{index}_indices"] = np.array(indices, dtype=np.int32)
        save_dict[f"f_{index}_indptr"] = np.array(indptr, dtype=np.int32)

    np.savez_compressed(output_path, **save_dict)


annotations = load_annotations(ANNOTATION_PATH)
shape = (annotations["video"]["height"], annotations["video"]["width"])
sample_source_frames = annotations["video"]["sample_source_frames"]
camera_segments = annotations["camera_segments"]
crowd_segments = annotations["crowd_segments"]

frame_labels = build_frame_labels(sample_source_frames, camera_segments)
intervals = merge_intervals(frame_labels)
masks = build_masks(sample_source_frames, crowd_segments, shape)

with INTERVAL_OUTPUT.open("w") as f:
    json.dump(intervals, f, indent=2, ensure_ascii=False)

save_sparse_masks(masks, shape, MASK_OUTPUT)
PY
