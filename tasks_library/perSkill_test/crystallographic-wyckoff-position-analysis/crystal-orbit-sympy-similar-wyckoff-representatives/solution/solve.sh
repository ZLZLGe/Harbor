#!/bin/bash
set -e

mkdir -p /root/workspace

cat > /root/workspace/wyckoff_orbit_solver.py <<'EOF'
#!/usr/bin/env python3

import json
from pathlib import Path

from sympy import Rational, floor, symbols, sympify


X, Y, Z = symbols("x y z")
SYMPY_LOCALS = {"x": X, "y": Y, "z": Z}
DEFAULT_INPUT = Path("/root/orbit_cards/wyckoff_orbit_cards.json")


def _parse_seed(seed):
    return tuple(Rational(sympify(value, locals=SYMPY_LOCALS)) for value in seed)


def _parse_operation(operation):
    parts = [part.strip() for part in operation.split(",")]
    return tuple(sympify(part, locals=SYMPY_LOCALS) for part in parts)


def _normalize_mod_one(value):
    normalized = sympify(value) - floor(sympify(value))
    return Rational(normalized)


def _apply_operation(operation, seed):
    substitutions = {X: seed[0], Y: seed[1], Z: seed[2]}
    return tuple(_normalize_mod_one(component.subs(substitutions)) for component in operation)


def _stringify_position(position):
    return [str(value) for value in position]


def analyze_wyckoff_orbits(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    result = {"cards": {}}

    for card in payload["cards"]:
        parsed_operations = [_parse_operation(operation) for operation in card["symmetry_operations"]]
        orbit_summary = {}

        for orbit in card["orbits"]:
            seed = _parse_seed(orbit["seed"])
            unique_positions = {_apply_operation(operation, seed) for operation in parsed_operations}
            sorted_positions = sorted(unique_positions)

            orbit_summary[orbit["label"]] = {
                "multiplicity": len(sorted_positions),
                "representative": _stringify_position(sorted_positions[0]),
                "positions": [_stringify_position(position) for position in sorted_positions],
            }

        result["cards"][card["card_id"]] = orbit_summary

    return result


def main():
    summary = analyze_wyckoff_orbits(str(DEFAULT_INPUT))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
EOF

chmod +x /root/workspace/wyckoff_orbit_solver.py
