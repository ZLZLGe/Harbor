#!/usr/bin/env python3

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from sympy import simplify, sympify, symbols


x = symbols("x")

EXPECTED = {
    "cantilever_two_stage": {
        "constants": {
            "C1": "11",
            "C2": "15",
            "D1": "-205/6",
            "D2": "-75/2",
        },
        "shear_segments": [
            {"start": "0", "end": "2", "expr": "11 - x**2/2"},
            {"start": "2", "end": "5", "expr": "15 - 3*x"},
        ],
        "moment_segments": [
            {"start": "0", "end": "2", "expr": "-x**3/6 + 11*x - 205/6"},
            {"start": "2", "end": "5", "expr": "-3*x**2/2 + 15*x - 75/2"},
        ],
        "evaluations": {
            "0": {"V": "11", "M": "-205/6"},
            "2": {"V": "9", "M": "-27/2"},
            "5": {"V": "0", "M": "0"},
        },
    },
    "simply_supported_linear": {
        "constants": {
            "C1": "22/3",
            "D1": "0",
        },
        "shear_segments": [
            {"start": "0", "end": "4", "expr": "-x**2 - x + 22/3"},
        ],
        "moment_segments": [
            {"start": "0", "end": "4", "expr": "-x**3/3 - x**2/2 + 22*x/3"},
        ],
        "evaluations": {
            "0": {"V": "22/3", "M": "0"},
            "2": {"V": "4/3", "M": "10"},
            "4": {"V": "-38/3", "M": "0"},
        },
    },
    "free_end_with_ramp_middle": {
        "constants": {
            "C1": "4",
            "C2": "7/2",
            "C3": "8",
            "D1": "-35/3",
            "D2": "-23/2",
            "D3": "-16",
        },
        "shear_segments": [
            {"start": "0", "end": "1", "expr": "4"},
            {"start": "1", "end": "3", "expr": "-x**2/2 + x + 7/2"},
            {"start": "3", "end": "4", "expr": "8 - 2*x"},
        ],
        "moment_segments": [
            {"start": "0", "end": "1", "expr": "4*x - 35/3"},
            {"start": "1", "end": "3", "expr": "-x**3/6 + x**2/2 + 7*x/2 - 23/2"},
            {"start": "3", "end": "4", "expr": "-x**2 + 8*x - 16"},
        ],
        "evaluations": {
            "0": {"V": "4", "M": "-35/3"},
            "1": {"V": "4", "M": "-23/3"},
            "3": {"V": "2", "M": "-1"},
            "4": {"V": "0", "M": "0"},
        },
    },
}


def parse_expr(text: str):
    return sympify(text, locals={"x": x})


def load_module():
    solution_path = Path("/root/workspace/beam_load_analyzer.py")
    if not solution_path.exists():
        raise FileNotFoundError(f"Missing solution file: {solution_path}")

    spec = importlib.util.spec_from_file_location("beam_load_analyzer", solution_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_reward(score: float) -> None:
    os.makedirs("/logs/verifier", exist_ok=True)
    Path("/logs/verifier/reward.txt").write_text(f"{score:.2f}\n")


def assert_symbolic_equal(actual_text: str, expected_text: str, label: str) -> None:
    actual_expr = parse_expr(actual_text)
    expected_expr = parse_expr(expected_text)
    if simplify(actual_expr - expected_expr) != 0:
        raise AssertionError(f"{label} mismatch: expected {expected_text!r}, got {actual_text!r}")


def compare_case(actual_case: dict, expected_case: dict, case_id: str) -> None:
    if set(actual_case.keys()) != {"constants", "shear_segments", "moment_segments", "evaluations"}:
        raise AssertionError(f"{case_id}: unexpected top-level keys {sorted(actual_case.keys())}")

    if set(actual_case["constants"].keys()) != set(expected_case["constants"].keys()):
        raise AssertionError(f"{case_id}: constant keys mismatch")
    for key, expected_value in expected_case["constants"].items():
        if key not in actual_case["constants"]:
            raise AssertionError(f"{case_id}: missing constant {key}")
        assert_symbolic_equal(actual_case["constants"][key], expected_value, f"{case_id} constant {key}")

    for section in ("shear_segments", "moment_segments"):
        actual_segments = actual_case[section]
        expected_segments = expected_case[section]
        if len(actual_segments) != len(expected_segments):
            raise AssertionError(f"{case_id}: {section} length mismatch")
        for index, (actual_segment, expected_segment) in enumerate(zip(actual_segments, expected_segments), start=1):
            if actual_segment.get("start") != expected_segment["start"] or actual_segment.get("end") != expected_segment["end"]:
                raise AssertionError(f"{case_id}: {section} interval mismatch at segment {index}")
            if "expr" not in actual_segment:
                raise AssertionError(f"{case_id}: missing expr in {section} segment {index}")
            assert_symbolic_equal(
                actual_segment["expr"],
                expected_segment["expr"],
                f"{case_id} {section} segment {index}",
            )

    if set(actual_case["evaluations"].keys()) != set(expected_case["evaluations"].keys()):
        raise AssertionError(f"{case_id}: evaluation points mismatch")
    for point, expected_values in expected_case["evaluations"].items():
        actual_values = actual_case["evaluations"].get(point)
        if actual_values is None:
            raise AssertionError(f"{case_id}: missing evaluation point {point}")
        for quantity, expected_value in expected_values.items():
            if quantity not in actual_values:
                raise AssertionError(f"{case_id}: missing {quantity} at point {point}")
            assert_symbolic_equal(
                actual_values[quantity],
                expected_value,
                f"{case_id} evaluation {point} {quantity}",
            )


def compare_result(actual: dict, expected: dict) -> None:
    if set(actual.keys()) != set(expected.keys()):
        raise AssertionError(f"Case keys mismatch: expected {sorted(expected.keys())}, got {sorted(actual.keys())}")
    for case_id, expected_case in expected.items():
        if case_id not in actual:
            raise AssertionError(f"Missing case {case_id}")
        compare_case(actual[case_id], expected_case, case_id)


def main() -> int:
    total_checks = 0
    passed_checks = 0

    try:
        module = load_module()
        if not hasattr(module, "reconstruct_beam_response"):
            raise AttributeError("Missing reconstruct_beam_response(filepath) function")

        result = module.reconstruct_beam_response("/root/data/beam_cases.json")
        total_checks += 1
        compare_result(result, EXPECTED)
        passed_checks += 1

        subprocess.run([sys.executable, "/root/workspace/beam_load_analyzer.py"], check=True)
        output_path = Path("/root/workspace/beam_load_results.json")
        if not output_path.exists():
            raise FileNotFoundError("Missing /root/workspace/beam_load_results.json")
        written = json.loads(output_path.read_text())
        total_checks += 1
        compare_result(written, EXPECTED)
        passed_checks += 1

    except Exception as exc:
        print(f"Test execution failed: {exc}")
        write_reward(0.0)
        return 1

    score = passed_checks / total_checks if total_checks else 0.0
    print(f"Passed {passed_checks}/{total_checks} checks.")
    write_reward(score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
