#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


INPUT_DIR = Path("/root/inputs")
OUTPUT_PATH = Path("/root/workspace/normalization_manifest.json")
SUPPORTED_SUFFIXES = {".cif", ".vasp"}
SYMPREC = 1e-3
ANGLE_TOLERANCE = 5

sys.path.insert(0, "/root/workspace")


def round_float(value: float) -> float:
    return round(float(value), 6)


def detect_input_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".cif":
        return "cif"
    if suffix == ".vasp":
        return "poscar"
    raise ValueError(f"unsupported structure format: {path.name}")


def load_structure(path: Path) -> Structure:
    input_format = detect_input_format(path)
    if input_format == "cif":
        return Structure.from_file(path)
    return Poscar.from_file(path).structure


def summarize_structure(structure: Structure) -> dict[str, Any]:
    return {
        "formula": structure.composition.formula,
        "site_count": len(structure),
        "volume": round_float(structure.volume),
        "volume_per_atom": round_float(structure.volume / len(structure)),
    }


def build_expected_sample(path: Path) -> dict[str, Any]:
    original = load_structure(path)
    analyzer = SpacegroupAnalyzer(
        original,
        symprec=SYMPREC,
        angle_tolerance=ANGLE_TOLERANCE,
    )
    primitive = analyzer.get_primitive_standard_structure()
    conventional = analyzer.get_conventional_standard_structure()

    original_summary = summarize_structure(original)
    primitive_summary = summarize_structure(primitive)
    conventional_summary = summarize_structure(conventional)

    comparisons_to_original = []
    original_volume = float(original.volume)
    original_volume_per_atom = original_volume / len(original)
    for target_name, target_summary in (
        ("primitive", primitive_summary),
        ("conventional", conventional_summary),
    ):
        target_structure = primitive if target_name == "primitive" else conventional
        target_volume = float(target_structure.volume)
        target_volume_per_atom = target_volume / len(target_structure)
        comparisons_to_original.append(
            {
                "target": target_name,
                "formula": target_summary["formula"],
                "site_count": target_summary["site_count"],
                "volume_ratio_to_original": round_float(target_volume / original_volume),
                "volume_per_atom_delta": round_float(
                    target_volume_per_atom - original_volume_per_atom
                ),
            }
        )

    return {
        "input_format": detect_input_format(path),
        "original": original_summary,
        "primitive": primitive_summary,
        "conventional": conventional_summary,
        "comparisons_to_original": comparisons_to_original,
    }


def expected_manifest() -> dict[str, Any]:
    sample_paths = sorted(
        path
        for path in INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    sample_order = [path.name for path in sample_paths]
    samples = {path.name: build_expected_sample(path) for path in sample_paths}
    return {
        "input_directory": str(INPUT_DIR),
        "sample_count": len(sample_paths),
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
    print("Testing structure normalization manifest")
    print("=" * 80)

    try:
        solution = importlib.import_module("solution")
        build_manifest = getattr(solution, "build_normalization_manifest", None)
        assert callable(build_manifest), "build_normalization_manifest is not callable"
        print("1. Entry function exists")
        passed_checks += 1
    except Exception as exc:
        print(f"1. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        actual_manifest = build_manifest(str(INPUT_DIR))
        assert isinstance(actual_manifest, dict), "returned manifest must be a dict"
        print("2. Function returns a dict manifest")
        passed_checks += 1
    except Exception as exc:
        print(f"2. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        expected = expected_manifest()
        assert actual_manifest == expected, (
            "returned manifest does not match independent normalization analysis"
        )
        print("3. Returned manifest matches independent normalization analysis")
        passed_checks += 1
    except Exception as exc:
        print(f"3. FAILED: {exc}")
        traceback.print_exc()

    try:
        assert OUTPUT_PATH.exists(), f"{OUTPUT_PATH} was not created"
        file_manifest = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        assert file_manifest == actual_manifest, (
            "JSON file content does not match function return value"
        )
        print("4. JSON output file exists and matches the returned manifest")
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
