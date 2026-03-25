#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import csv
import json
from pathlib import Path

import numpy as np


TRACE_PATH = Path("/root/data/station_trace.csv")
CATALOG_PATH = Path("/root/data/template_catalog.json")
OUTPUT_PATH = Path("/root/seismic_arrivals.json")


def load_trace() -> np.ndarray:
    amplitudes = []
    with TRACE_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            amplitudes.append(float(row["amplitude"]))
    return np.asarray(amplitudes, dtype=np.float64)


def pick_arrivals(trace: np.ndarray, template_cfg: dict, sample_rate_hz: float, trace_start_time_s: float):
    template = np.asarray(template_cfg["samples"], dtype=np.float64)
    score = np.abs(np.correlate(trace, template, mode="valid"))
    picks = []
    min_separation = int(template_cfg["min_separation_samples"])
    threshold = float(template_cfg["detection_threshold"])
    template_length = int(template.size)

    for idx in np.argsort(score)[::-1]:
        peak = float(score[idx])
        if peak < threshold:
            break
        arrival_sample = int(idx)
        if any(abs(arrival_sample - item["arrival_sample"]) < min_separation for item in picks):
            continue
        picks.append(
            {
                "arrival_sample": arrival_sample,
                "arrival_time_s": round(
                    trace_start_time_s + (arrival_sample + template_length / 2.0) / sample_rate_hz,
                    6,
                ),
                "match_score": round(peak, 6),
            }
        )

    picks.sort(key=lambda item: item["arrival_sample"])
    return picks


def main():
    trace = load_trace()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    sample_rate_hz = float(catalog["sample_rate_hz"])
    trace_start_time_s = float(catalog["trace_start_time_s"])

    detections = {}
    for template_cfg in catalog["templates"]:
        detections[str(template_cfg["event_type"])] = pick_arrivals(
            trace,
            template_cfg,
            sample_rate_hz,
            trace_start_time_s,
        )

    output = {
        "station_id": str(catalog["station_id"]),
        "detections": detections,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
