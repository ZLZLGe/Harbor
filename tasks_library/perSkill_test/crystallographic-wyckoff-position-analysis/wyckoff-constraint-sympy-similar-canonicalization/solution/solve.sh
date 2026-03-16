#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/wyckoff_constraint_solver.py <<'PY'
#!/usr/bin/env python3
import json
from pathlib import Path

from sympy import Rational, simplify, solve, symbols, sympify


def _normalize_mod_one(value):
    normalized = simplify(value % 1)
    if normalized == 1:
        normalized = Rational(0)
    return normalized


def _to_rational_strings(values):
    return [str(_normalize_mod_one(value)) for value in values]


def solve_wyckoff_constraint_cases(filepath: str) -> dict[str, dict]:
    payload = json.loads(Path(filepath).read_text())
    results = {}

    for case in payload["cases"]:
        symbol_names = case["parameter_symbols"]
        case_symbols = symbols(" ".join(symbol_names))
        if not isinstance(case_symbols, tuple):
            case_symbols = (case_symbols,)
        local_dict = dict(zip(symbol_names, case_symbols))

        representative = [
            sympify(expr, locals=local_dict)
            for expr in case["representative_constraints"]
        ]
        sample_point = [
            Rational(text).limit_denominator(case["max_denominator"])
            for text in case["sample_point"]
        ]

        equations = [expr - value for expr, value in zip(representative, sample_point)]
        solutions = solve(equations, case_symbols, dict=True)
        if len(solutions) != 1:
            raise ValueError(f"expected a unique solution for {case['case_id']}")
        solved_parameters = solutions[0]

        normalized_representative = [
            _normalize_mod_one(expr.subs(solved_parameters))
            for expr in representative
        ]

        normalized_orbit = set()
        for coordinate_triplet in case["orbit_constraints"]:
            exprs = [sympify(expr, locals=local_dict) for expr in coordinate_triplet]
            normalized_triplet = tuple(
                _normalize_mod_one(expr.subs(solved_parameters)) for expr in exprs
            )
            normalized_orbit.add(normalized_triplet)

        results[case["case_id"]] = {
            "parameters": {
                name: str(simplify(solved_parameters[local_dict[name]]))
                for name in symbol_names
            },
            "canonical_representative": _to_rational_strings(normalized_representative),
            "orbit_multiplicity": len(normalized_orbit),
        }

    return results


if __name__ == "__main__":
    input_path = "/root/data/wyckoff_constraint_cases.json"
    output_path = Path("/root/workspace/wyckoff_constraint_results.json")
    output_path.write_text(
        json.dumps(solve_wyckoff_constraint_cases(input_path), indent=2, sort_keys=True) + "\n"
    )
PY

chmod +x /root/workspace/wyckoff_constraint_solver.py
python3 /root/workspace/wyckoff_constraint_solver.py
