#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import csv
import json
from pathlib import Path

import numpy as np


def to_complex_array(pairs):
    return np.array([complex(i, q) for i, q in pairs], dtype=np.complex128)


catalog = json.loads(Path("/root/data/preamble_catalog.json").read_text())
segments_doc = json.loads(Path("/root/data/received_segments.json").read_text())

preambles = {
    item["preamble_id"]: to_complex_array(item["samples"])
    for item in catalog["preambles"]
}

rows = []
for segment in sorted(segments_doc["segments"], key=lambda item: item["segment_id"]):
    samples = to_complex_array(segment["samples"])
    best = None

    for preamble_id, template in preambles.items():
        limit = len(samples) - len(template) + 1
        scores = np.empty(limit, dtype=np.float64)
        for k in range(limit):
            scores[k] = abs(np.vdot(template, samples[k : k + len(template)]))

        start_index = int(scores.argmax())
        peak_score = float(scores[start_index])
        candidate = (peak_score, preamble_id, start_index)

        if best is None:
            best = candidate
            continue

        if peak_score > best[0]:
            best = candidate
        elif peak_score == best[0]:
            if preamble_id < best[1] or (preamble_id == best[1] and start_index < best[2]):
                best = candidate

    rows.append(
        {
            "segment_id": segment["segment_id"],
            "preamble_id": best[1],
            "start_index": best[2],
            "peak_score": f"{best[0]:.6f}",
        }
    )

with open("/root/frame_sync_results.csv", "w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["segment_id", "preamble_id", "start_index", "peak_score"],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
