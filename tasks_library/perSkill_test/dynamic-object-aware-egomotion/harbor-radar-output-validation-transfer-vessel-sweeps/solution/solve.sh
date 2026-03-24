#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")
SWEEPS_PATH = ROOT / "harbor_radar_sweeps.json"
COMPONENTS_PATH = ROOT / "harbor_echo_components.json"
OUTPUT_JSON = ROOT / "pred_harbor_tracks.json"
OUTPUT_MASKS = ROOT / "pred_harbor_echo_masks.npz"


def rect_to_mask(mask, rect):
    top = int(rect["top"])
    left = int(rect["left"])
    height = int(rect["height"])
    width = int(rect["width"])
    mask[top:top + height, left:left + width] = True


def dense_to_csr(mask):
    height, _ = mask.shape
    data = []
    indices = []
    indptr = [0]
    for row in range(height):
        cols = np.flatnonzero(mask[row])
        indices.extend(int(col) for col in cols)
        data.extend([True] * len(cols))
        indptr.append(len(indices))
    return (
        np.array(data, dtype=bool),
        np.array(indices, dtype=np.int32),
        np.array(indptr, dtype=np.int32),
    )


with SWEEPS_PATH.open(encoding="utf-8") as f:
    sweeps = json.load(f)

with COMPONENTS_PATH.open(encoding="utf-8") as f:
    components = json.load(f)

track_mapping = {
    f"{segment['start']}->{segment['end']}": [segment["label"]]
    for segment in sweeps["maneuver_segments"]
}

shape = tuple(int(v) for v in components["shape"])
payload = {"shape": np.array(shape, dtype=np.int32)}

for frame_idx, scan in enumerate(components["scans"]):
    mask = np.zeros(shape, dtype=bool)
    for component in scan["components"]:
        if component["active"]:
            rect_to_mask(mask, component)
    data, indices, indptr = dense_to_csr(mask)
    payload[f"f_{frame_idx}_data"] = data
    payload[f"f_{frame_idx}_indices"] = indices
    payload[f"f_{frame_idx}_indptr"] = indptr

OUTPUT_JSON.write_text(
    json.dumps(track_mapping, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
np.savez_compressed(OUTPUT_MASKS, **payload)
PY
