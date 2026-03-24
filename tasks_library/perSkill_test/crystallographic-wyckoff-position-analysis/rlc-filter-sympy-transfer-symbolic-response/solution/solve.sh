#!/bin/bash

set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/rlc_symbolic_response.py <<'EOF'
#!/usr/bin/env python3

import csv
from collections import OrderedDict

from sympy import Poly, Rational, default_sort_key, expand, limit, oo, simplify, symbols


s = symbols("s")


def _parse_exact(text: str):
    return Rational(text)


def _probe_numerator(output_probe, resistance, inductance, capacitance):
    if output_probe == "capacitor":
        return simplify(1)
    if output_probe == "resistor":
        return simplify(resistance * capacitance * s)
    if output_probe == "inductor":
        return simplify(inductance * capacitance * s**2)
    raise ValueError(f"Unsupported output_probe: {output_probe}")


def _damping_class(denominator):
    polynomial = Poly(denominator, s)
    a, b, c = polynomial.all_coeffs()
    discriminant = simplify(b**2 - 4 * a * c)
    if discriminant == 0:
        return "critically_damped"
    if discriminant > 0:
        return "overdamped"
    return "underdamped"


def analyze_rlc_filters(filepath: str) -> dict:
    filters = OrderedDict()

    with open(filepath, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            resistance = _parse_exact(row["R_ohm"])
            inductance = _parse_exact(row["L_henry"])
            capacitance = _parse_exact(row["C_farad"])

            numerator = expand(_probe_numerator(row["output_probe"], resistance, inductance, capacitance))
            denominator = expand(inductance * capacitance * s**2 + resistance * capacitance * s + 1)
            transfer_function = simplify(numerator / denominator)
            poles = [
                str(simplify(root))
                for root in sorted(Poly(denominator, s).all_roots(), key=default_sort_key)
            ]

            filters[row["filter_id"]] = {
                "numerator_polynomial": str(numerator),
                "denominator_polynomial": str(denominator),
                "transfer_function": str(transfer_function),
                "poles": poles,
                "damping_class": _damping_class(denominator),
                "dc_limit": str(simplify(limit(transfer_function, s, 0))),
                "high_frequency_limit": str(simplify(limit(transfer_function, s, oo))),
            }

    return {"filters": filters}
EOF
