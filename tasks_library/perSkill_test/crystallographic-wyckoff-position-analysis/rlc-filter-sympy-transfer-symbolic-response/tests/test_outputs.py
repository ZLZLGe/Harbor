#!/usr/bin/env python3

import csv
import os
import sys
from collections import Counter

from sympy import Poly, Rational, default_sort_key, limit, oo, simplify, sympify, symbols

sys.path.insert(0, "/root/workspace")

from rlc_symbolic_response import analyze_rlc_filters


INPUT_PATH = "/root/filter_bank/rlc_filter_bank.csv"
s = symbols("s")


def _parse_exact(text: str):
    return Rational(text)


def _expected_row(row):
    resistance = _parse_exact(row["R_ohm"])
    inductance = _parse_exact(row["L_henry"])
    capacitance = _parse_exact(row["C_farad"])

    denominator = simplify(inductance * capacitance * s**2 + resistance * capacitance * s + 1)

    if row["output_probe"] == "capacitor":
        numerator = simplify(1)
    elif row["output_probe"] == "resistor":
        numerator = simplify(resistance * capacitance * s)
    elif row["output_probe"] == "inductor":
        numerator = simplify(inductance * capacitance * s**2)
    else:
        raise ValueError(f"Unexpected output_probe: {row['output_probe']}")

    polynomial = Poly(denominator, s)
    a, b, c = polynomial.all_coeffs()
    discriminant = simplify(b**2 - 4 * a * c)
    if discriminant == 0:
        damping_class = "critically_damped"
    elif discriminant > 0:
        damping_class = "overdamped"
    else:
        damping_class = "underdamped"

    transfer_function = simplify(numerator / denominator)
    poles = sorted((simplify(root) for root in polynomial.all_roots()), key=default_sort_key)
    return {
        "numerator": simplify(numerator),
        "denominator": simplify(denominator),
        "transfer_function": transfer_function,
        "poles": poles,
        "damping_class": damping_class,
        "dc_limit": simplify(limit(transfer_function, s, 0)),
        "high_frequency_limit": simplify(limit(transfer_function, s, oo)),
    }


def _parse_expression(text: str):
    return simplify(sympify(text, locals={"s": s}, rational=True))


def main():
    with open(INPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    result = analyze_rlc_filters(INPUT_PATH)
    actual_filters = result.get("filters", {})

    total_checks = 0
    passed_checks = 0
    failures = []

    total_checks += 1
    if list(actual_filters.keys()) == [row["filter_id"] for row in rows]:
        passed_checks += 1
    else:
        failures.append("filter order mismatch")

    for row in rows:
        filter_id = row["filter_id"]
        expected = _expected_row(row)
        actual = actual_filters.get(filter_id)

        total_checks += 1
        if actual is not None:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: missing filter output")
            continue

        total_checks += 1
        actual_numerator = _parse_expression(actual["numerator_polynomial"])
        if simplify(actual_numerator - expected["numerator"]) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: numerator mismatch")

        total_checks += 1
        actual_denominator = _parse_expression(actual["denominator_polynomial"])
        if simplify(actual_denominator - expected["denominator"]) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: denominator mismatch")

        total_checks += 1
        if actual_denominator.subs({s: 0}) == 1:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: denominator constant term is not 1")

        total_checks += 1
        actual_transfer = _parse_expression(actual["transfer_function"])
        if simplify(actual_transfer - expected["transfer_function"]) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: transfer function mismatch")

        total_checks += 1
        if simplify(actual_transfer - actual_numerator / actual_denominator) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: transfer function is inconsistent with numerator/denominator")

        total_checks += 1
        actual_poles = [_parse_expression(entry) for entry in actual["poles"]]
        if Counter(map(str, sorted(actual_poles, key=default_sort_key))) == Counter(
            map(str, sorted(expected["poles"], key=default_sort_key))
        ):
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: pole set mismatch")

        total_checks += 1
        reconstructed = simplify(actual_denominator)
        roots_ok = True
        for pole in actual_poles:
            if simplify(reconstructed.subs({s: pole})) != 0:
                roots_ok = False
                break
        if roots_ok:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: reported poles do not satisfy denominator")

        total_checks += 1
        if actual["damping_class"] == expected["damping_class"]:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: damping classification mismatch")

        total_checks += 1
        actual_dc = _parse_expression(actual["dc_limit"])
        if simplify(actual_dc - expected["dc_limit"]) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: dc limit mismatch")

        total_checks += 1
        actual_hf = _parse_expression(actual["high_frequency_limit"])
        if simplify(actual_hf - expected["high_frequency_limit"]) == 0:
            passed_checks += 1
        else:
            failures.append(f"{filter_id}: high-frequency limit mismatch")

    score = passed_checks / total_checks if total_checks else 0.0

    print("=" * 80)
    print("Transfer task: symbolic RLC filter response")
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
