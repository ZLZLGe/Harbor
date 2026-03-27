#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/root")

from steady_state_lab import build_report, load_problem


REPORT_PATH = Path("/root/similar_phase_space_report.json")


def assert_close(actual, expected, tol=1e-6):
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol), f"{actual} != {expected}"


def test_report_matches_reference():
    assert REPORT_PATH.exists(), "missing similar_phase_space_report.json"
    actual = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    expected = build_report(load_problem("/root/steady_state_cases.json"))

    assert actual["grid"] == expected["grid"]
    assert actual["ranking_by_mean_photon"] == expected["ranking_by_mean_photon"]
    assert len(actual["cases"]) == len(expected["cases"]) == 4

    for actual_case, expected_case in zip(actual["cases"], expected["cases"]):
        assert actual_case["case_id"] == expected_case["case_id"]
        for key in [
            "mean_photon",
            "qubit_excitation",
            "wigner_center",
            "wigner_min",
            "wigner_max",
            "normalization",
        ]:
            assert_close(actual_case[key], expected_case[key])
        assert len(actual_case["centerline_signature"]) == 5
        for actual_value, expected_value in zip(
            actual_case["centerline_signature"],
            expected_case["centerline_signature"],
        ):
            assert_close(actual_value, expected_value)
