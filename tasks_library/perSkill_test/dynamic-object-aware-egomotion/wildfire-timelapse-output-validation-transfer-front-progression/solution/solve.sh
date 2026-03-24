#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"

python3 <<'PY'
import csv
import json
import os
from pathlib import Path

import numpy as np

TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
MANIFEST_PATH = TASK_ROOT / "wildfire_sampling_manifest.csv"
RUNS_PATH = TASK_ROOT / "wildfire_fireline_runs.json"
OUTPUT_JSON = TASK_ROOT / "pred_fire_progression.json"
OUTPUT_MASKS = TASK_ROOT / "pred_fireline_masks.npz"

VALID_LABELS = {"初始点火", "顺风扩展", "峡谷跃进", "侧翼回燃"}


def load_manifest(path: Path):
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["sample_index"] = int(row["sample_index"])
        row["front_edge_col"] = int(row["front_edge_col"])
        row["wind_kph"] = int(row["wind_kph"])
    return rows


def merge_phase_intervals(rows):
    phase_rows = [
        (row["sample_index"], row["phase_to_next"])
        for row in rows
        if row["phase_to_next"]
    ]

    intervals = {}
    start_idx, current_label = phase_rows[0]
    previous_idx = start_idx

    for sample_index, label in phase_rows[1:]:
        if sample_index != previous_idx + 1:
            raise ValueError("sample_index is not continuous")
        if label != current_label:
            intervals[f"{start_idx}->{previous_idx + 1}"] = [current_label]
            start_idx = sample_index
            current_label = label
        previous_idx = sample_index

    intervals[f"{start_idx}->{previous_idx + 1}"] = [current_label]
    return intervals


def load_fireline_masks(path: Path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    shape = tuple(int(v) for v in payload["shape"])
    masks = []
    for snapshot in sorted(payload["snapshots"], key=lambda item: int(item["sample_index"])):
        mask = np.zeros(shape, dtype=bool)
        for segment in snapshot["segments"]:
            row = int(segment["row"])
            for start, end in segment["col_ranges"]:
                mask[row, int(start):int(end)] = True
        masks.append(mask)
    return shape, masks


def mask_to_csr(mask):
    indices = []
    indptr = [0]
    for row in mask:
        cols = np.flatnonzero(row)
        indices.extend(cols.tolist())
        indptr.append(len(indices))
    data = np.ones(len(indices), dtype=bool)
    return data, np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int32)


def validate_intervals(intervals, num_samples):
    cursor = 0
    items = sorted(intervals.items(), key=lambda item: int(item[0].split("->")[0]))
    for key, labels in items:
        start, end = map(int, key.split("->"))
        if start != cursor:
            raise ValueError(f"gap or overlap near {key}")
        if end <= start:
            raise ValueError(f"invalid interval {key}")
        if len(labels) != 1 or labels[0] not in VALID_LABELS:
            raise ValueError(f"invalid labels for {key}: {labels}")
        cursor = end
    if cursor != num_samples - 1:
        raise ValueError("intervals do not cover all sample intervals")


def validate_sparse_pack(shape, dense_masks, sparse_payload):
    height, width = shape
    if tuple(sparse_payload["shape"].tolist()) != shape:
        raise ValueError("shape mismatch")
    if len(dense_masks) == 0:
        raise ValueError("no masks generated")

    for frame_idx, expected_mask in enumerate(dense_masks):
        data = sparse_payload[f"f_{frame_idx}_data"]
        indices = sparse_payload[f"f_{frame_idx}_indices"]
        indptr = sparse_payload[f"f_{frame_idx}_indptr"]
        if indptr.shape != (height + 1,):
            raise ValueError(f"invalid indptr shape for frame {frame_idx}")
        if int(indptr[0]) != 0 or int(indptr[-1]) != len(indices) or len(indices) != len(data):
            raise ValueError(f"broken csr lengths for frame {frame_idx}")
        if len(indices):
            if int(indices.min()) < 0 or int(indices.max()) >= width:
                raise ValueError(f"indices out of bounds for frame {frame_idx}")
        rebuilt = np.zeros(shape, dtype=bool)
        for row in range(height):
            start, end = int(indptr[row]), int(indptr[row + 1])
            rebuilt[row, indices[start:end]] = True
        if not np.array_equal(rebuilt, expected_mask):
            raise ValueError(f"roundtrip mismatch for frame {frame_idx}")


manifest_rows = load_manifest(MANIFEST_PATH)
intervals = merge_phase_intervals(manifest_rows)
shape, dense_masks = load_fireline_masks(RUNS_PATH)

validate_intervals(intervals, len(manifest_rows))

sparse_payload = {"shape": np.asarray(shape, dtype=np.int32)}
for frame_idx, mask in enumerate(dense_masks):
    data, indices, indptr = mask_to_csr(mask)
    sparse_payload[f"f_{frame_idx}_data"] = data
    sparse_payload[f"f_{frame_idx}_indices"] = indices
    sparse_payload[f"f_{frame_idx}_indptr"] = indptr

validate_sparse_pack(shape, dense_masks, sparse_payload)

with open(OUTPUT_JSON, "w", encoding="utf-8") as handle:
    json.dump(intervals, handle, ensure_ascii=False, indent=2)

np.savez(OUTPUT_MASKS, **sparse_payload)
PY
