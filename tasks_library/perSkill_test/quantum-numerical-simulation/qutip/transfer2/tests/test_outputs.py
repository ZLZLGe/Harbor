#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/root")

from entanglement_lab import build_report, load_problem


REPORT_PATH = Path("/root/transfer2_entanglement_summary.json")


def assert_close(actual, expected, tol=1e-6):
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol), f"{actual} != {expected}"


def test_entanglement_summary_matches_reference():
    assert REPORT_PATH.exists(), "missing transfer2_entanglement_summary.json"
    actual = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    expected = build_report(load_problem("/root/entanglement_cases.json"))

    assert actual["time_grid"] == expected["time_grid"]
    assert actual["ranking_by_final_concurrence"] == expected["ranking_by_final_concurrence"]
    assert len(actual["cases"]) == len(expected["cases"]) == 3

    for actual_case, expected_case in zip(actual["cases"], expected["cases"]):
        assert actual_case["case_id"] == expected_case["case_id"]
        for key in [
            "initial_concurrence",
            "final_concurrence",
            "min_concurrence",
            "half_life_time",
            "max_entropy_qubit_a",
            "mean_total_excitation",
        ]:
            assert_close(actual_case[key], expected_case[key])
