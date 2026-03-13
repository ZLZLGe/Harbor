#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/coordination_shell_signature.py <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations

import math
from collections import Counter
from typing import Any

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from sympy import Rational, nsimplify, sqrt


SYMPREC = 1e-3
ANGLE_TOLERANCE = 5
DISTANCE_TOLERANCE = 1e-5
WRAP_TOLERANCE = 1e-8
MAX_DENOMINATOR = 48
NSIMPLIFY_CONSTANTS = [
    sqrt(2),
    sqrt(3),
    sqrt(5),
    sqrt(6),
    sqrt(7),
    sqrt(8),
    sqrt(10),
    sqrt(11),
    sqrt(12),
]


def _clean_small(value: float) -> float:
    return 0.0 if abs(float(value)) < WRAP_TOLERANCE else float(value)


def _wrap_fractional_component(value: float) -> float:
    wrapped = ((float(value) + 0.5) % 1.0) - 0.5
    if math.isclose(wrapped, -0.5, abs_tol=WRAP_TOLERANCE):
        wrapped = 0.5
    return _clean_small(wrapped)


def _rational_string(value: float) -> str:
    return str(Rational(str(_clean_small(value))).limit_denominator(MAX_DENOMINATOR))


def _ratio_string(value: float) -> str:
    expr = nsimplify(float(value), NSIMPLIFY_CONSTANTS, tolerance=1e-10, rational=True)
    if getattr(expr, "is_Float", False):
        expr = Rational(str(float(value))).limit_denominator(MAX_DENOMINATOR)
    return str(expr)


def _ordered_site_symbol(site) -> str:
    if hasattr(site, "specie"):
        specie = site.specie
        if hasattr(specie, "symbol"):
            return specie.symbol
        if hasattr(specie, "element") and hasattr(specie.element, "symbol"):
            return specie.element.symbol
    return str(site.species_string)


def _get_wyckoffs(dataset) -> list[str]:
    if hasattr(dataset, "wyckoffs"):
        return list(dataset.wyckoffs)
    return list(dataset["wyckoffs"])


def analyze_coordination_shell_signature(filepath: str) -> dict[str, Any]:
    structure = Structure.from_file(filepath)
    initial_analyzer = SpacegroupAnalyzer(
        structure,
        symprec=SYMPREC,
        angle_tolerance=ANGLE_TOLERANCE,
    )
    conventional = initial_analyzer.get_conventional_standard_structure(
        international_monoclinic=True
    )
    analyzer = SpacegroupAnalyzer(
        conventional,
        symprec=SYMPREC,
        angle_tolerance=ANGLE_TOLERANCE,
    )
    dataset = analyzer.get_symmetry_dataset()
    symmetrized = analyzer.get_symmetrized_structure()

    if dataset is None:
        raise ValueError(f"Failed to obtain symmetry dataset for {filepath}")

    wyckoffs = _get_wyckoffs(dataset)
    search_radius = max(10.0, max(conventional.lattice.abc))

    site_signatures: list[dict[str, Any]] = []
    for group in sorted(symmetrized.equivalent_indices, key=min):
        rep_index = min(group)
        site = conventional[rep_index]
        neighbors = [
            neighbor
            for neighbor in conventional.get_neighbors(site, search_radius)
            if float(neighbor.nn_distance) > DISTANCE_TOLERANCE
        ]
        if not neighbors:
            raise ValueError(f"No neighbors found for site index {rep_index} in {filepath}")

        min_distance = min(float(neighbor.nn_distance) for neighbor in neighbors)
        shell_neighbors = [
            neighbor
            for neighbor in neighbors
            if float(neighbor.nn_distance) <= min_distance + DISTANCE_TOLERANCE
        ]

        shell_entries = []
        count_by_element: Counter[str] = Counter()
        for neighbor in shell_neighbors:
            element = _ordered_site_symbol(neighbor)
            count_by_element[element] += 1
            displacement = [
                _wrap_fractional_component(neighbor.frac_coords[i] - site.frac_coords[i])
                for i in range(3)
            ]
            shell_entries.append(
                (
                    element,
                    tuple(displacement),
                    {
                        "element": element,
                        "fractional_offset": [_rational_string(value) for value in displacement],
                        "distance_ratio": _ratio_string(float(neighbor.nn_distance) / min_distance),
                    },
                )
            )

        shell_entries.sort(key=lambda item: (item[0], item[1]))

        site_signatures.append(
            {
                "site_index": rep_index,
                "species": _ordered_site_symbol(site),
                "wyckoff_letter": str(wyckoffs[rep_index]),
                "coordination_number": len(shell_entries),
                "neighbor_element_counts": dict(sorted(count_by_element.items())),
                "shell_signature": [item[2] for item in shell_entries],
            }
        )

    site_signatures.sort(key=lambda item: item["site_index"])

    return {
        "spacegroup_number": int(analyzer.get_space_group_number()),
        "spacegroup_symbol": str(analyzer.get_space_group_symbol()),
        "site_signatures": site_signatures,
    }
EOF

echo "Wrote /root/workspace/coordination_shell_signature.py"
