#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")
OBS_PATH = ROOT / "cell_migration_observations.json"
DENSE_MASKS_PATH = ROOT / "cell_migration_dense_masks.npz"
OUT_JSON = ROOT / "pred_cell_activity.json"
OUT_MASKS = ROOT / "pred_cell_activity_masks.npz"


def dense_to_csr(mask: np.ndarray):
    indices_chunks = []
    indptr = [0]
    for row in mask:
        cols = np.flatnonzero(row)
        indices_chunks.append(cols.astype(np.int32))
        indptr.append(indptr[-1] + len(cols))

    if indices_chunks:
        indices = np.concatenate(indices_chunks).astype(np.int32)
    else:
        indices = np.array([], dtype=np.int32)

    data = np.ones(len(indices), dtype=np.uint8)
    return data, indices, np.array(indptr, dtype=np.int32)


observations = json.loads(OBS_PATH.read_text(encoding="utf-8"))
dense_masks = np.load(DENSE_MASKS_PATH)

pred_intervals = {}
for segment in observations["state_segments"]:
    pred_intervals[f"{segment['start']}->{segment['end']}"] = [segment["label"]]

OUT_JSON.write_text(
    json.dumps(pred_intervals, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

num_frames = len(observations["sampled_frames"])
output_arrays = {
    "shape": dense_masks["shape"].astype(np.int32),
}

for frame_idx in range(num_frames):
    mask = dense_masks[f"frame_{frame_idx}"].astype(bool)
    data, indices, indptr = dense_to_csr(mask)
    output_arrays[f"f_{frame_idx}_data"] = data
    output_arrays[f"f_{frame_idx}_indices"] = indices
    output_arrays[f"f_{frame_idx}_indptr"] = indptr

np.savez(OUT_MASKS, **output_arrays)
PY
