#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/solid_state_stoichiometry.py <<'EOF'
#!/usr/bin/env python3

from math import gcd
from functools import reduce
import json

from sympy import Matrix


def _gcd_many(values):
    return reduce(gcd, values)


def _lcm_many(values):
    def pairwise_lcm(left, right):
        return left * right // gcd(left, right)

    return reduce(pairwise_lcm, values, 1)


def _format_term(name, coefficient):
    if coefficient == 1:
        return name
    return f"{coefficient} {name}"


def _normalize_integer_vector(vector):
    denominators = [value.q for value in vector]
    scale = _lcm_many(denominators)
    integers = [int(value * scale) for value in vector]
    sign = 1
    for value in integers:
        if value != 0:
            sign = 1 if value > 0 else -1
            break
    integers = [value * sign for value in integers]
    common = _gcd_many([abs(value) for value in integers if value != 0])
    return [value // common for value in integers]


def _build_balance_matrix(species, elements):
    rows = []
    for element in elements:
        row = []
        for species_info in species["precursors"]:
            row.append(species_info["elements"].get(element, 0))
        row.append(-species["target"]["elements"].get(element, 0))
        for species_info in species["byproducts"]:
            row.append(-species_info["elements"].get(element, 0))
        rows.append(row)
    return Matrix(rows)


def _element_totals(species_list, coefficients):
    totals = {}
    for coefficient, species in zip(coefficients, species_list):
        for element, count in species["elements"].items():
            totals[element] = totals.get(element, 0) + coefficient * count
    return totals


def balance_solid_state_reactions(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    results = {}

    for reaction in payload["reactions"]:
        elements = sorted(
            {
                element
                for species in reaction["precursors"] + [reaction["target"]] + reaction["byproducts"]
                for element in species["elements"]
            }
        )

        matrix = _build_balance_matrix(reaction, elements)
        basis = matrix.nullspace()
        if len(basis) != 1:
            raise ValueError(f"Expected a one-dimensional nullspace for {reaction['reaction_id']}")

        coefficients = _normalize_integer_vector(basis[0])
        precursor_count = len(reaction["precursors"])
        byproduct_count = len(reaction["byproducts"])

        precursor_coeffs = coefficients[:precursor_count]
        target_coeff = coefficients[precursor_count]
        byproduct_coeffs = coefficients[precursor_count + 1 : precursor_count + 1 + byproduct_count]

        if any(value <= 0 for value in precursor_coeffs + [target_coeff] + byproduct_coeffs):
            raise ValueError(f"Non-positive coefficient found for {reaction['reaction_id']}")

        left_terms = [
            _format_term(species["name"], coefficient)
            for species, coefficient in zip(reaction["precursors"], precursor_coeffs)
        ]
        right_terms = [_format_term(reaction["target"]["name"], target_coeff)] + [
            _format_term(species["name"], coefficient)
            for species, coefficient in zip(reaction["byproducts"], byproduct_coeffs)
        ]

        left_totals = _element_totals(reaction["precursors"], precursor_coeffs)
        right_species = [reaction["target"]] + reaction["byproducts"]
        right_totals = _element_totals(right_species, [target_coeff] + byproduct_coeffs)

        element_balance = {}
        for element in elements:
            element_balance[element] = {
                "left": left_totals.get(element, 0),
                "right": right_totals.get(element, 0),
                "balanced": left_totals.get(element, 0) == right_totals.get(element, 0),
            }

        results[reaction["reaction_id"]] = {
            "coefficients": {
                "precursors": {
                    species["name"]: coefficient
                    for species, coefficient in zip(reaction["precursors"], precursor_coeffs)
                },
                "target": {reaction["target"]["name"]: target_coeff},
                "byproducts": {
                    species["name"]: coefficient
                    for species, coefficient in zip(reaction["byproducts"], byproduct_coeffs)
                },
            },
            "normalized_equation": " + ".join(left_terms) + " -> " + " + ".join(right_terms),
            "element_balance": element_balance,
        }

    return {"reactions": results}
EOF

echo "Solution written to /root/workspace/solid_state_stoichiometry.py"
