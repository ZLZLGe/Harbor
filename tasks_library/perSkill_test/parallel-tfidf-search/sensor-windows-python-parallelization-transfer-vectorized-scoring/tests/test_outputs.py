#!/usr/bin/env python3

from __future__ import annotations

import csv
import importlib.util
import math
import os
import sys
import time
from pathlib import Path
from statistics import median

import pytest


WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
WINDOWS_PATH = WORKSPACE_ROOT / "sensor_windows.npz"
MANIFEST_PATH = WORKSPACE_ROOT / "window_manifest.json"
sys.path.insert(0, str(WORKSPACE_ROOT))

from sensor_scoring_sequential import score_sensor_windows_sequential, write_window_score_report_sequential


def load_vectorized_module():
    module_path = WORKSPACE_ROOT / "vectorized_scores.py"
    if not module_path.exists():
        pytest.fail(f"Expected output file was not created: {module_path}")

    spec = importlib.util.spec_from_file_location("vectorized_scores", module_path)
    if spec is None or spec.loader is None:
        pytest.fail(f"Unable to load module from {module_path}")

    sys.modules.pop("vectorized_scores", None)
    module = importlib.util.module_from_spec(spec)
    sys.modules["vectorized_scores"] = module
    spec.loader.exec_module(module)
    return module


FLOAT_FIELDS = ("mean_level", "volatility", "spike_score", "drift_score", "anomaly_score")


def assert_scores_match(expected_scores, actual_scores):
    assert len(expected_scores) == len(actual_scores)
    for expected, actual in zip(expected_scores, actual_scores):
        assert expected.window_id == actual.window_id
        assert expected.device_id == actual.device_id
        assert expected.start_tick == actual.start_tick
        assert expected.end_tick == actual.end_tick
        assert expected.breach_count == actual.breach_count
        assert expected.severity_band == actual.severity_band
        for field in FLOAT_FIELDS:
            assert math.isclose(
                getattr(expected, field),
                getattr(actual, field),
                rel_tol=0.0,
                abs_tol=1e-6,
            ), f"{field} mismatch for window {expected.window_id}"


def assert_summary_match(expected_summary, actual_summary):
    assert expected_summary["batch_id"] == actual_summary["batch_id"]
    assert expected_summary["window_count"] == actual_summary["window_count"]
    assert expected_summary["rolling_width"] == actual_summary["rolling_width"]
    assert expected_summary["threshold_z"] == actual_summary["threshold_z"]
    assert expected_summary["severity_counts"] == actual_summary["severity_counts"]
    assert expected_summary["top_windows"] == actual_summary["top_windows"]
    assert expected_summary["device_hotspots"] == actual_summary["device_hotspots"]
    assert expected_summary["total_breach_count"] == actual_summary["total_breach_count"]
    assert math.isclose(
        expected_summary["mean_anomaly_score"],
        actual_summary["mean_anomaly_score"],
        rel_tol=0.0,
        abs_tol=1e-6,
    )
    assert math.isclose(
        expected_summary["max_anomaly_score"],
        actual_summary["max_anomaly_score"],
        rel_tol=0.0,
        abs_tol=1e-6,
    )


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def benchmark_scoring(module, repeats=3):
    sequential_times = []
    vectorized_times = []

    score_sensor_windows_sequential(windows_path=WINDOWS_PATH, manifest_path=MANIFEST_PATH)
    module.score_sensor_windows_vectorized(windows_path=WINDOWS_PATH, manifest_path=MANIFEST_PATH)

    for _ in range(repeats):
        start = time.perf_counter()
        score_sensor_windows_sequential(windows_path=WINDOWS_PATH, manifest_path=MANIFEST_PATH)
        sequential_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        module.score_sensor_windows_vectorized(windows_path=WINDOWS_PATH, manifest_path=MANIFEST_PATH)
        vectorized_times.append(time.perf_counter() - start)

    return median(sequential_times), median(vectorized_times)


class TestInterface:
    def test_output_file_and_functions_exist(self):
        module = load_vectorized_module()
        assert hasattr(module, "score_sensor_windows_vectorized")
        assert hasattr(module, "write_window_score_report")


class TestCorrectness:
    def test_vectorized_scores_match_baseline(self):
        module = load_vectorized_module()
        expected = score_sensor_windows_sequential(windows_path=WINDOWS_PATH, manifest_path=MANIFEST_PATH)

        start = time.perf_counter()
        actual = module.score_sensor_windows_vectorized(
            windows_path=WINDOWS_PATH,
            manifest_path=MANIFEST_PATH,
            chunk_size=512,
        )
        wall_time = time.perf_counter() - start

        assert actual.window_count == expected.window_count
        assert_scores_match(expected.scores, actual.scores)
        assert_summary_match(expected.summary, actual.summary)
        assert abs(actual.elapsed_time - wall_time) < 0.20

    def test_report_writer_matches_baseline_csv_and_summary(self, tmp_path):
        module = load_vectorized_module()
        expected_output = tmp_path / "expected_window_scores.csv"
        actual_output = tmp_path / "actual_window_scores.csv"

        expected_summary = write_window_score_report_sequential(
            windows_path=WINDOWS_PATH,
            manifest_path=MANIFEST_PATH,
            output_path=expected_output,
        )
        actual_summary = module.write_window_score_report(
            windows_path=WINDOWS_PATH,
            manifest_path=MANIFEST_PATH,
            output_path=actual_output,
            chunk_size=512,
        )

        assert_summary_match(expected_summary, actual_summary)
        assert read_csv_rows(expected_output) == read_csv_rows(actual_output)


class TestPerformance:
    def test_vectorized_scoring_speedup(self):
        module = load_vectorized_module()
        sequential_time, vectorized_time = benchmark_scoring(module)
        speedup = sequential_time / vectorized_time

        print(f"\nSequential median: {sequential_time:.4f}s")
        print(f"Vectorized median: {vectorized_time:.4f}s")
        print(f"Speedup:           {speedup:.3f}x")

        assert speedup >= 3.00
