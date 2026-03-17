#!/bin/bash
set -e

mkdir -p /root/workspace

cat > /root/workspace/beam_load_analyzer.py <<'EOF'
#!/usr/bin/env python3

import json
from pathlib import Path

from sympy import integrate, simplify, solve, sstr, symbols, sympify


x = symbols("x")


def _parse_exact(value: str):
    return sympify(value, locals={"x": x})


def _select_segment_index(segments: list[dict], point) -> int:
    for index, segment in enumerate(segments):
        start = _parse_exact(segment["start"])
        end = _parse_exact(segment["end"])
        if start <= point <= end:
            return index
    raise ValueError(f"Point {point} is outside the beam domain")


def reconstruct_beam_response(filepath: str) -> dict[str, dict]:
    payload = json.loads(Path(filepath).read_text())
    results: dict[str, dict] = {}

    for case in payload["cases"]:
        segments = case["segments"]
        segment_count = len(segments)
        c_symbols = list(symbols(f"C1:{segment_count + 1}"))
        d_symbols = list(symbols(f"D1:{segment_count + 1}"))

        shear_exprs = []
        moment_exprs = []
        equations = []

        for index, segment in enumerate(segments):
            load_expr = _parse_exact(segment["load"])
            shear_expr = simplify(integrate(-load_expr, x) + c_symbols[index])
            moment_expr = simplify(integrate(shear_expr, x) + d_symbols[index])
            shear_exprs.append(shear_expr)
            moment_exprs.append(moment_expr)

        for index in range(segment_count - 1):
            boundary = _parse_exact(segments[index]["end"])
            equations.append(
                simplify(shear_exprs[index].subs(x, boundary) - shear_exprs[index + 1].subs(x, boundary))
            )
            equations.append(
                simplify(moment_exprs[index].subs(x, boundary) - moment_exprs[index + 1].subs(x, boundary))
            )

        for boundary_condition in case["boundary_conditions"]:
            point = _parse_exact(boundary_condition["x"])
            value = _parse_exact(boundary_condition["value"])
            segment_index = _select_segment_index(segments, point)
            target_expr = shear_exprs[segment_index] if boundary_condition["quantity"] == "V" else moment_exprs[segment_index]
            equations.append(simplify(target_expr.subs(x, point) - value))

        solved = solve(equations, c_symbols + d_symbols, dict=True)
        if len(solved) != 1:
            raise ValueError(f"Expected a unique solution for constants, got {len(solved)}")
        constant_values = solved[0]

        constants: dict[str, str] = {}
        for symbol in c_symbols + d_symbols:
            constants[sstr(symbol)] = sstr(simplify(constant_values[symbol]))

        shear_segments = []
        moment_segments = []
        for index, segment in enumerate(segments):
            solved_shear = simplify(shear_exprs[index].subs(constant_values))
            solved_moment = simplify(moment_exprs[index].subs(constant_values))
            shear_segments.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "expr": sstr(solved_shear),
                }
            )
            moment_segments.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "expr": sstr(solved_moment),
                }
            )

        evaluations: dict[str, dict[str, str]] = {}
        for query in case["query_points"]:
            point = _parse_exact(query)
            segment_index = _select_segment_index(segments, point)
            solved_shear = simplify(shear_exprs[segment_index].subs(constant_values).subs(x, point))
            solved_moment = simplify(moment_exprs[segment_index].subs(constant_values).subs(x, point))
            evaluations[query] = {
                "V": sstr(solved_shear),
                "M": sstr(solved_moment),
            }

        results[case["case_id"]] = {
            "constants": constants,
            "shear_segments": shear_segments,
            "moment_segments": moment_segments,
            "evaluations": evaluations,
        }

    return results


if __name__ == "__main__":
    input_path = "/root/data/beam_cases.json"
    output_path = Path("/root/workspace/beam_load_results.json")
    output_path.write_text(json.dumps(reconstruct_beam_response(input_path), indent=2, sort_keys=True))
EOF

chmod +x /root/workspace/beam_load_analyzer.py
echo "Wrote /root/workspace/beam_load_analyzer.py"
