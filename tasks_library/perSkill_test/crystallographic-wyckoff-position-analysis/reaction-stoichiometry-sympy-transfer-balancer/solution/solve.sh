#!/bin/bash
set -e

mkdir -p /root/workspace

cat > /root/workspace/reaction_balancer.py <<'EOF'
#!/usr/bin/env python3

import json
import math
from collections import defaultdict
from pathlib import Path

from sympy import Matrix, Rational


def _parse_number(text: str, index: int) -> tuple[int, int]:
    start = index
    while index < len(text) and text[index].isdigit():
        index += 1
    if start == index:
        return 1, index
    return int(text[start:index]), index


def _parse_formula(formula: str) -> dict[str, int]:
    formula = formula.strip()

    def parse_group(index: int) -> tuple[dict[str, int], int]:
        counts: dict[str, int] = defaultdict(int)
        while index < len(formula):
            char = formula[index]
            if char == "(":
                inner_counts, index = parse_group(index + 1)
                multiplier, index = _parse_number(formula, index)
                for element, amount in inner_counts.items():
                    counts[element] += amount * multiplier
                continue
            if char == ")":
                return dict(counts), index + 1
            if char.isupper():
                end = index + 1
                while end < len(formula) and formula[end].islower():
                    end += 1
                element = formula[index:end]
                multiplier, end = _parse_number(formula, end)
                counts[element] += multiplier
                index = end
                continue
            raise ValueError(f"Unsupported formula token {char!r} in {formula!r}")
        return dict(counts), index

    parsed, final_index = parse_group(0)
    if final_index != len(formula):
        raise ValueError(f"Failed to parse full formula {formula!r}")
    return parsed


def _parse_reaction(equation: str) -> tuple[list[str], list[str], list[str], list[list[int]]]:
    if "->" not in equation:
        raise ValueError(f"Missing reaction arrow in {equation!r}")

    reactant_text, product_text = equation.split("->", maxsplit=1)
    reactants = [part.strip() for part in reactant_text.split("+") if part.strip()]
    products = [part.strip() for part in product_text.split("+") if part.strip()]
    if not reactants or not products:
        raise ValueError(f"Invalid reaction sides in {equation!r}")

    species = reactants + products
    compositions = [_parse_formula(item) for item in species]
    elements = sorted({element for composition in compositions for element in composition})

    matrix: list[list[int]] = []
    for element in elements:
        row = []
        for idx, composition in enumerate(compositions):
            sign = 1 if idx < len(reactants) else -1
            row.append(sign * composition.get(element, 0))
        matrix.append(row)

    return reactants, products, elements, matrix


def _canonical_basis(matrix_rows: list[list[int]]) -> list[Rational]:
    nullspace = Matrix(matrix_rows).nullspace()
    if len(nullspace) != 1:
        raise ValueError(f"Expected a one-dimensional nullspace, got {len(nullspace)}")

    basis_vector = [Rational(value) for value in nullspace[0]]
    pivot = next((value for value in basis_vector if value != 0), None)
    if pivot is None:
        raise ValueError("Nullspace basis is the zero vector")

    normalized = [value / pivot for value in basis_vector]
    if any(value < 0 for value in normalized):
        normalized = [-value for value in normalized]
        pivot = next((value for value in normalized if value != 0), None)
        normalized = [value / pivot for value in normalized]
    return normalized


def _integer_coefficients(basis: list[Rational]) -> list[int]:
    denominators = [value.q for value in basis]
    scale = 1
    for denominator in denominators:
        scale = math.lcm(scale, denominator)

    integers = [int(value * scale) for value in basis]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    if divisor == 0:
        raise ValueError("Cannot reduce all-zero coefficient vector")
    return [value // divisor for value in integers]


def _format_balanced_equation(reactants: list[str], products: list[str], coefficients: list[int]) -> str:
    left_coeffs = coefficients[: len(reactants)]
    right_coeffs = coefficients[len(reactants) :]

    def format_term(coeff: int, species: str) -> str:
        if coeff == 1:
            return species
        return f"{coeff} {species}"

    left = " + ".join(format_term(coeff, species) for coeff, species in zip(left_coeffs, reactants))
    right = " + ".join(format_term(coeff, species) for coeff, species in zip(right_coeffs, products))
    return f"{left} -> {right}"


def balance_reaction_cases(filepath: str) -> dict[str, dict]:
    data = json.loads(Path(filepath).read_text())
    results: dict[str, dict] = {}

    for case in data["cases"]:
        case_id = case["case_id"]
        reactants, products, elements, matrix = _parse_reaction(case["equation"])
        basis = _canonical_basis(matrix)
        coefficients = _integer_coefficients(basis)

        results[case_id] = {
            "reactants": reactants,
            "products": products,
            "elements": elements,
            "stoichiometry_matrix": matrix,
            "nullspace_basis": [str(value) for value in basis],
            "integer_coefficients": coefficients,
            "balanced_equation": _format_balanced_equation(reactants, products, coefficients),
        }

    return results


if __name__ == "__main__":
    input_path = "/root/data/reaction_cases.json"
    output_path = Path("/root/workspace/reaction_balancer_results.json")
    output_path.write_text(json.dumps(balance_reaction_cases(input_path), indent=2, sort_keys=True))
EOF

chmod +x /root/workspace/reaction_balancer.py
echo "Wrote /root/workspace/reaction_balancer.py"
