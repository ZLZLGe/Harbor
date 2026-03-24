#!/usr/bin/env python3

from __future__ import annotations

import gc
import importlib.util
import json
import sys
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from telemetry_baseline import compute_window_statistics_baseline
from telemetry_common import TelemetryWindowSummary, summary_to_dict
from telemetry_factory import write_telemetry_csv

WORKSPACE = Path("/root/workspace")
FIXTURE_CSV = WORKSPACE / "telemetry_fixture.csv"
EXPECTED_JSON = WORKSPACE / "expected_telemetry_summary.json"
SOLUTION_PATH = WORKSPACE / "telemetry_window_solution.py"


def load_solution():
    if not SOLUTION_PATH.exists():
        pytest.fail("missing /root/workspace/telemetry_window_solution.py")

    spec = importlib.util.spec_from_file_location("telemetry_window_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["telemetry_window_solution"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def solution():
    return load_solution()


def normalize(summaries):
    return [summary_to_dict(summary) for summary in summaries]


def measure_peak_bytes(func, *args, **kwargs):
    gc.collect()
    tracemalloc.start()
    try:
        result = func(*args, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


class TestSolutionShape:
    def test_module_exports_required_functions(self, solution):
        assert hasattr(solution, "compute_window_statistics")
        assert hasattr(solution, "write_anomaly_summary_json")


class TestFixtureBehavior:
    def test_fixture_matches_expected_json(self, solution, tmp_path):
        summaries = solution.compute_window_statistics(FIXTURE_CSV)
        assert summaries
        assert all(isinstance(item, TelemetryWindowSummary) for item in summaries)

        observed = normalize(summaries)
        expected = json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
        assert observed == expected

        output_path = tmp_path / "fixture-summary.json"
        solution.write_anomaly_summary_json(FIXTURE_CSV, output_path)
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written == expected


class TestGeneratedTelemetry:
    @pytest.mark.parametrize(
        ("num_sensors", "samples_per_sensor", "seed", "window_size", "anomaly_sigma"),
        [
            (4, 70, 17, 6, 1.8),
            (7, 140, 29, 12, 2.25),
            (9, 210, 61, 10, 2.0),
        ],
    )
    def test_generated_csv_matches_baseline(
        self,
        solution,
        tmp_path,
        num_sensors,
        samples_per_sensor,
        seed,
        window_size,
        anomaly_sigma,
    ):
        csv_path = tmp_path / f"telemetry-{seed}.csv"
        row_count = write_telemetry_csv(
            csv_path,
            num_sensors=num_sensors,
            samples_per_sensor=samples_per_sensor,
            seed=seed,
        )
        assert row_count == num_sensors * samples_per_sensor

        expected = normalize(
            compute_window_statistics_baseline(
                csv_path,
                window_size=window_size,
                anomaly_sigma=anomaly_sigma,
            )
        )
        observed = normalize(
            solution.compute_window_statistics(
                csv_path,
                window_size=window_size,
                anomaly_sigma=anomaly_sigma,
            )
        )
        assert observed == expected


class TestMemoryBudget:
    def test_peak_memory_is_far_below_baseline(self, solution, tmp_path):
        csv_path = tmp_path / "large-telemetry.csv"
        row_count = write_telemetry_csv(
            csv_path,
            num_sensors=28,
            samples_per_sensor=3200,
            seed=404,
        )
        assert row_count > 80000

        baseline_result, baseline_peak = measure_peak_bytes(
            compute_window_statistics_baseline,
            csv_path,
            12,
            2.25,
        )
        candidate_result, candidate_peak = measure_peak_bytes(
            solution.compute_window_statistics,
            csv_path,
            12,
            2.25,
        )

        assert normalize(candidate_result) == normalize(baseline_result)
        assert candidate_peak < baseline_peak * 0.4, (
            f"candidate peak {candidate_peak} not below 40% of baseline peak {baseline_peak}"
        )
        assert candidate_peak < 24 * 1024 * 1024, f"candidate peak too high: {candidate_peak} bytes"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
