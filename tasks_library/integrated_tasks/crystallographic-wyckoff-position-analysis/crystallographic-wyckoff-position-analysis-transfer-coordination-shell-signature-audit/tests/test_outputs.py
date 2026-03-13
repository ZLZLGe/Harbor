#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import os
import shutil
import tempfile
import traceback
from collections import Counter
from pathlib import Path

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


def reference_solution(filepath: str) -> dict:
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
    site_signatures = []

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


def load_candidate_function():
    module_path = Path("/root/workspace/coordination_shell_signature.py")
    if not module_path.exists():
        raise FileNotFoundError("Missing /root/workspace/coordination_shell_signature.py")

    spec = importlib.util.spec_from_file_location("candidate_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    func = getattr(module, "analyze_coordination_shell_signature", None)
    if func is None:
        raise AttributeError("Function analyze_coordination_shell_signature not found")
    return func


def run_single_case(func, cif_path: Path) -> None:
    expected = reference_solution(str(cif_path))
    actual = func(str(cif_path))
    if actual != expected:
        raise AssertionError(
            f"Mismatch for {cif_path.name}\nExpected: {expected}\nActual:   {actual}"
        )


def run_renamed_case(func, source_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        renamed = Path(tmpdir) / "renamed_input_case.cif"
        shutil.copy2(source_path, renamed)
        expected = reference_solution(str(renamed))
        actual = func(str(renamed))
        if actual != expected:
            raise AssertionError(
                f"Mismatch for renamed copy of {source_path.name}\nExpected: {expected}\nActual:   {actual}"
            )


def main() -> int:
    case_dir = Path("/root/coordination_cases")
    cases = sorted(case_dir.glob("*.cif"))
    if not cases:
        raise FileNotFoundError("No CIF files found in /root/coordination_cases")

    total_tests = 0
    passed_tests = 0
    failures: list[str] = []

    print("=" * 80)
    print("Testing coordination-shell signature audit")
    print("=" * 80)

    try:
        func = load_candidate_function()
    except Exception as exc:
        print(f"Failed to import candidate solution: {exc}")
        traceback.print_exc()
        os.makedirs("/logs/verifier", exist_ok=True)
        with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
            handle.write("0.00\n")
        return 0

    for cif_path in cases:
        total_tests += 1
        print(f"\nTest {total_tests}: {cif_path.name}")
        print("-" * 80)
        try:
            run_single_case(func, cif_path)
            print("PASS")
            passed_tests += 1
        except Exception as exc:
            print(f"FAIL: {exc}")
            traceback.print_exc()
            failures.append(cif_path.name)

    renamed_targets = [cases[0], cases[-1]]
    for cif_path in renamed_targets:
        total_tests += 1
        print(f"\nTest {total_tests}: renamed copy of {cif_path.name}")
        print("-" * 80)
        try:
            run_renamed_case(func, cif_path)
            print("PASS")
            passed_tests += 1
        except Exception as exc:
            print(f"FAIL: {exc}")
            traceback.print_exc()
            failures.append(f"renamed::{cif_path.name}")

    score = passed_tests / total_tests if total_tests else 0.0

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failures)}")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    print(f"Score: {score:.2f}")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
