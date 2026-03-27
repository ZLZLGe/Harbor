#!/usr/bin/env python3
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, "/root")

from oscillator_relaxation_lab import FIELDNAMES, build_rows, load_problem


OUTPUT_PATH = Path("/root/transfer1_relaxation_metrics.csv")


def assert_close(actual, expected, tol=1e-6):
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol), f"{actual} != {expected}"


def test_relaxation_csv_matches_reference():
    assert OUTPUT_PATH.exists(), "missing transfer1_relaxation_metrics.csv"
    expected_rows = build_rows(load_problem("/root/relaxation_cases.json"))

    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_rows = list(reader)

    assert reader.fieldnames == FIELDNAMES
    assert len(actual_rows) == len(expected_rows) == 3

    for actual, expected in zip(actual_rows, expected_rows):
        assert actual["case_id"] == expected["case_id"]
        for key in FIELDNAMES[1:]:
            assert_close(float(actual[key]), expected[key])
