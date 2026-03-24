#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

from pymatgen.analysis.local_env import CrystalNN
from pymatgen.core import Structure


STRUCTURE_DIR = Path("/root/coordination_inputs")
TARGET_SPEC_PATH = Path("/root/coordination_targets.json")
OUTPUT_PATH = Path("/root/workspace/coordination_signatures.json")
TOLERANCE = 1e-4
NN_FINDER = CrystalNN(
    distance_cutoffs=None,
    x_diff_weight=0.0,
    porous_adjustment=False,
)

sys.path.insert(0, "/root/workspace")


def round_float(value: float) -> float:
    return round(float(value), 6)


def normalize_frac_coords(frac_coords: list[float] | tuple[float, float, float]) -> list[float]:
    return [float(value) % 1.0 for value in frac_coords]


def periodic_match(a: list[float], b: list[float], tol: float = TOLERANCE) -> bool:
    for left, right in zip(a, b, strict=True):
        delta = abs(left - right)
        if min(delta, 1.0 - delta) > tol:
            return False
    return True


def locate_site_index(structure: Structure, target_frac_coords: list[float]) -> int:
    normalized_target = normalize_frac_coords(target_frac_coords)
    matches = []
    for index, site in enumerate(structure):
        site_coords = normalize_frac_coords(site.frac_coords.tolist())
        if periodic_match(site_coords, normalized_target):
            matches.append(index)
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one site match, got {matches}")
    return matches[0]


def get_element_symbol(site) -> str:
    return site.species.elements[0].symbol


def build_neighbor_formula(neighbor_composition: dict[str, int]) -> str:
    return "-".join(f"{element}{count}" for element, count in sorted(neighbor_composition.items()))


def build_expected_target(structure: Structure, target: dict[str, Any]) -> dict[str, Any]:
    site_index = locate_site_index(structure, target["fractional_coords"])
    center_site = structure[site_index]
    neighbor_info = NN_FINDER.get_nn_info(structure, site_index)
    assert neighbor_info, f"no neighbors found for {target['label']}"

    neighbor_counter = Counter(get_element_symbol(item["site"]) for item in neighbor_info)
    neighbor_composition = dict(sorted(neighbor_counter.items()))

    distances = [
        round_float(structure.get_distance(site_index, item["site_index"], jimage=item["image"]))
        for item in neighbor_info
    ]
    min_distance = min(distances)
    max_distance = max(distances)
    center_element = get_element_symbol(center_site)
    coordination_number = len(neighbor_info)
    neighbor_formula = build_neighbor_formula(neighbor_composition)

    return {
        "label": target["label"],
        "site_index": site_index,
        "center_element": center_element,
        "fractional_coords": [
            round_float(value) for value in normalize_frac_coords(center_site.frac_coords.tolist())
        ],
        "coordination_number": coordination_number,
        "neighbor_composition": neighbor_composition,
        "nearest_bond_length_range": [min_distance, max_distance],
        "coordination_signature": (
            f"{center_element}:CN{coordination_number}:{neighbor_formula}:"
            f"{min_distance:.6f}-{max_distance:.6f}"
        ),
    }


def build_expected_manifest() -> dict[str, Any]:
    target_spec = json.loads(TARGET_SPEC_PATH.read_text(encoding="utf-8"))
    sample_order = sorted(target_spec["samples"])
    samples = {}

    for sample_name in sample_order:
        structure = Structure.from_file(STRUCTURE_DIR / sample_name)
        targets = [
            build_expected_target(structure, target)
            for target in target_spec["samples"][sample_name]
        ]
        samples[sample_name] = {
            "formula": structure.composition.formula,
            "target_count": len(targets),
            "targets": targets,
        }

    return {
        "structure_directory": str(STRUCTURE_DIR),
        "target_spec_path": str(TARGET_SPEC_PATH),
        "sample_count": len(sample_order),
        "sample_order": sample_order,
        "samples": samples,
    }


def write_reward(score: float) -> None:
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")


def main() -> int:
    total_checks = 4
    passed_checks = 0

    print("=" * 80)
    print("Testing coordination signature analysis")
    print("=" * 80)

    try:
        solution = importlib.import_module("solution")
        build_manifest = getattr(solution, "build_coordination_signatures", None)
        assert callable(build_manifest), "build_coordination_signatures is not callable"
        print("1. Entry function exists")
        passed_checks += 1
    except Exception as exc:
        print(f"1. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        actual_manifest = build_manifest(str(STRUCTURE_DIR), str(TARGET_SPEC_PATH))
        assert isinstance(actual_manifest, dict), "returned value must be a dict"
        print("2. Function returns a dict manifest")
        passed_checks += 1
    except Exception as exc:
        print(f"2. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        expected_manifest = build_expected_manifest()
        assert actual_manifest == expected_manifest, (
            "returned manifest does not match independent coordination analysis"
        )
        print("3. Returned manifest matches independent coordination analysis")
        passed_checks += 1
    except Exception as exc:
        print(f"3. FAILED: {exc}")
        traceback.print_exc()

    try:
        assert OUTPUT_PATH.exists(), f"{OUTPUT_PATH} was not created"
        file_manifest = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        assert file_manifest == actual_manifest, (
            "JSON file content does not match the returned manifest"
        )
        print("4. JSON output file exists and matches returned manifest")
        passed_checks += 1
    except Exception as exc:
        print(f"4. FAILED: {exc}")
        traceback.print_exc()

    score = passed_checks / total_checks
    print("\nScore: {:.2f}".format(score))
    write_reward(score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
