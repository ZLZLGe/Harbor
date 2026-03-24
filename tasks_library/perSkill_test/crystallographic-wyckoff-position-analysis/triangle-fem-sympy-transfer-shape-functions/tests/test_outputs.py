#!/usr/bin/env python3

import os
import sys
import tomllib
from pathlib import Path

from sympy import Rational, simplify, sympify, symbols

sys.path.insert(0, "/root/workspace")

from triangle_shape_functions import derive_triangle_shape_data


INPUT_PATH = Path("/root/triangle_cases/triangle_cases.toml")
x, y = symbols("x y")

EXPECTED = {
    "bracket_web_panel": {
        "area": "15/8",
        "shape_functions": [
            "1 - 2*x/5 - 8*y/15",
            "2*x/5 - 2*y/15",
            "2*y/3",
        ],
        "gradient_matrix": [
            ["-2/5", "-8/15"],
            ["2/5", "-2/15"],
            ["0", "2/3"],
        ],
        "query_values": {
            "sensor_probe": ["8/15", "2/15", "1/3"],
            "stiffener_probe": ["16/45", "19/45", "2/9"],
        },
    },
    "gusset_cutout_patch": {
        "area": "7/4",
        "shape_functions": [
            "6/7 - 3*x/7 - 2*y/7",
            "4*x/7 - 2*y/7 + 5/14",
            "-x/7 + 4*y/7 - 3/14",
        ],
        "gradient_matrix": [
            ["-3/7", "-2/7"],
            ["4/7", "-2/7"],
            ["-1/7", "4/7"],
        ],
        "query_values": {
            "web_midpoint": ["2/7", "2/7", "3/7"],
            "fillet_probe": ["13/21", "2/7", "2/21"],
        },
    },
    "thermal_sensor_pad": {
        "area": "2",
        "shape_functions": [
            "-x/2 - y/4 + 7/12",
            "x/2 - y/4 + 1/4",
            "y/2 + 1/6",
        ],
        "gradient_matrix": [
            ["-1/2", "-1/4"],
            ["1/2", "-1/4"],
            ["0", "1/2"],
        ],
        "query_values": {
            "centroid_like_probe": ["1/3", "1/3", "1/3"],
            "edge_bias_probe": ["5/12", "1/12", "1/2"],
        },
    },
}


def _load_cases():
    with open(INPUT_PATH, "rb") as handle:
        payload = tomllib.load(handle)
    return payload["cases"]


def _parse_exact(value):
    if isinstance(value, int):
        return Rational(value)
    return simplify(sympify(str(value), rational=True))


def _parse_expression(text):
    return simplify(sympify(text, locals={"x": x, "y": y}, rational=True))


def _parse_gradient_row(row):
    return [_parse_exact(entry) for entry in row]


def main():
    result = derive_triangle_shape_data(str(INPUT_PATH))
    cases = _load_cases()

    total_checks = 0
    passed_checks = 0
    failures = []

    total_checks += 1
    actual_case_ids = list(result.get("cases", {}).keys())
    expected_case_ids = [case["case_id"] for case in cases]
    if actual_case_ids == expected_case_ids:
        passed_checks += 1
    else:
        failures.append("case order mismatch")

    for case in cases:
        case_id = case["case_id"]
        actual = result.get("cases", {}).get(case_id)
        expected = EXPECTED[case_id]

        total_checks += 1
        if actual is not None:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: missing case output")
            continue

        total_checks += 1
        if actual.get("area") == expected["area"]:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: area mismatch")

        total_checks += 1
        if actual.get("gradient_matrix") == expected["gradient_matrix"]:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: gradient matrix mismatch")

        total_checks += 1
        if actual.get("query_values") == expected["query_values"]:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: query values mismatch")

        actual_functions = actual.get("shape_functions", [])
        expected_functions = expected["shape_functions"]

        total_checks += 1
        if len(actual_functions) == 3:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: shape function count mismatch")
            continue

        actual_expressions = [_parse_expression(text) for text in actual_functions]
        expected_expressions = [_parse_expression(text) for text in expected_functions]

        total_checks += 1
        if all(simplify(left - right) == 0 for left, right in zip(actual_expressions, expected_expressions)):
            passed_checks += 1
        else:
            failures.append(f"{case_id}: shape functions not symbolically equivalent")

        total_checks += 1
        if simplify(sum(actual_expressions) - 1) == 0:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: partition of unity failed")

        total_checks += 1
        gradients_match = True
        for expression, gradient_row in zip(actual_expressions, actual.get("gradient_matrix", [])):
            expected_dx = simplify(expression.diff(x))
            expected_dy = simplify(expression.diff(y))
            parsed_row = _parse_gradient_row(gradient_row)
            if parsed_row != [expected_dx, expected_dy]:
                gradients_match = False
                break
        if gradients_match:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: gradients do not match derivatives")

        total_checks += 1
        nodal_property_ok = True
        for node_index, (px, py) in enumerate(case["nodes"]):
            substitutions = {x: _parse_exact(px), y: _parse_exact(py)}
            values = [simplify(expression.subs(substitutions)) for expression in actual_expressions]
            target = [Rational(1 if current_index == node_index else 0) for current_index in range(3)]
            if values != target:
                nodal_property_ok = False
                break
        if nodal_property_ok:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: nodal interpolation property failed")

        total_checks += 1
        query_order_ok = list(actual.get("query_values", {}).keys()) == [query["point_id"] for query in case["query_points"]]
        if query_order_ok:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: query point order mismatch")

        total_checks += 1
        query_substitution_ok = True
        for query in case["query_points"]:
            substitutions = {x: _parse_exact(query["x"]), y: _parse_exact(query["y"])}
            expected_values = [str(simplify(expression.subs(substitutions))) for expression in actual_expressions]
            if actual["query_values"].get(query["point_id"]) != expected_values:
                query_substitution_ok = False
                break
        if query_substitution_ok:
            passed_checks += 1
        else:
            failures.append(f"{case_id}: query substitution consistency failed")

    score = passed_checks / total_checks if total_checks else 0.0

    print("=" * 80)
    print("Transfer task: triangle FEM shape functions")
    print("=" * 80)
    print(f"Checks passed: {passed_checks}/{total_checks}")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")

    return 0 if score == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
