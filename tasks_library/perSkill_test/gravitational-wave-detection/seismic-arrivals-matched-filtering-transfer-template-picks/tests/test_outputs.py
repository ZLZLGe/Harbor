import csv
import json
import math
from pathlib import Path

import numpy as np


OUTPUT_PATH = Path("/root/seismic_arrivals.json")
TRACE_PATH = Path("/root/data/station_trace.csv")
CATALOG_PATH = Path("/root/data/template_catalog.json")
REQUIRED_PICK_KEYS = {"arrival_sample", "arrival_time_s", "match_score"}


def _load_trace() -> np.ndarray:
    amplitudes = []
    with TRACE_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["sample_index", "amplitude"], (
            f"unexpected columns in {TRACE_PATH}: {reader.fieldnames}"
        )
        for row in reader:
            amplitudes.append(float(row["amplitude"]))
    return np.asarray(amplitudes, dtype=np.float64)


def _expected_output():
    trace = _load_trace()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    sample_rate_hz = float(catalog["sample_rate_hz"])
    trace_start_time_s = float(catalog["trace_start_time_s"])

    detections = {}
    for template_cfg in catalog["templates"]:
        template = np.asarray(template_cfg["samples"], dtype=np.float64)
        score = np.abs(np.correlate(trace, template, mode="valid"))
        threshold = float(template_cfg["detection_threshold"])
        min_separation = int(template_cfg["min_separation_samples"])
        template_length = int(template.size)

        picks = []
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
        detections[str(template_cfg["event_type"])] = picks

    return {
        "station_id": str(catalog["station_id"]),
        "detections": detections,
    }


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_output_matches_expected_arrivals():
    expected = _expected_output()
    content = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert isinstance(content, dict), "output must be a JSON object"
    assert content.get("station_id") == expected["station_id"], "station_id must match template_catalog.json"

    actual_detections = content.get("detections")
    assert isinstance(actual_detections, dict), "detections must be a JSON object"
    assert set(actual_detections) == set(expected["detections"]), "detections keys must match event_type values"

    for event_type, expected_rows in expected["detections"].items():
        actual_rows = actual_detections[event_type]
        assert isinstance(actual_rows, list), f"detections[{event_type}] must be a list"
        assert actual_rows == sorted(actual_rows, key=lambda row: row["arrival_sample"]), (
            f"detections[{event_type}] must be sorted by arrival_sample"
        )
        assert len(actual_rows) == len(expected_rows), (
            f"detections[{event_type}] expected {len(expected_rows)} picks, got {len(actual_rows)}"
        )

        for actual_row, expected_row in zip(actual_rows, expected_rows):
            assert REQUIRED_PICK_KEYS.issubset(actual_row), (
                f"detections[{event_type}] rows must contain {sorted(REQUIRED_PICK_KEYS)}"
            )
            assert isinstance(actual_row["arrival_sample"], int), "arrival_sample must be an integer"
            assert isinstance(actual_row["arrival_time_s"], (int, float)), "arrival_time_s must be numeric"
            assert isinstance(actual_row["match_score"], (int, float)), "match_score must be numeric"
            assert math.isfinite(actual_row["arrival_time_s"]), "arrival_time_s must be finite"
            assert math.isfinite(actual_row["match_score"]), "match_score must be finite"

            assert actual_row["arrival_sample"] == expected_row["arrival_sample"]
            assert math.isclose(
                float(actual_row["arrival_time_s"]),
                expected_row["arrival_time_s"],
                rel_tol=0.0,
                abs_tol=1e-6,
            )
            assert math.isclose(
                float(actual_row["match_score"]),
                expected_row["match_score"],
                rel_tol=0.0,
                abs_tol=1e-6,
            )
