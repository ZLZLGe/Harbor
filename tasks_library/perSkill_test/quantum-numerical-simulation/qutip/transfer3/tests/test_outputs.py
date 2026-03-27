#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/root")

from gate_audit_lab import PROBE_ORDER, build_report, load_problem


REPORT_PATH = Path("/root/transfer3_gate_audit.json")


def assert_close(actual, expected, tol=1e-6):
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol), f"{actual} != {expected}"


def test_gate_audit_matches_reference():
    assert REPORT_PATH.exists(), "missing transfer3_gate_audit.json"
    actual = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    expected = build_report(load_problem("/root/gate_cases.json"))

    assert actual["target_gate"] == expected["target_gate"] == "rx_pi_over_2"
    assert actual["best_candidate"] == expected["best_candidate"]
    assert actual["ranking"] == expected["ranking"]
    assert len(actual["candidates"]) == len(expected["candidates"]) == 3

    for actual_case, expected_case in zip(actual["candidates"], expected["candidates"]):
        assert actual_case["case_id"] == expected_case["case_id"]
        for key in ["average_fidelity", "max_infidelity", "total_duration"]:
            assert_close(actual_case[key], expected_case[key])
        assert list(actual_case["probe_fidelities"].keys()) == PROBE_ORDER
        for label in PROBE_ORDER:
            assert_close(actual_case["probe_fidelities"][label], expected_case["probe_fidelities"][label])
