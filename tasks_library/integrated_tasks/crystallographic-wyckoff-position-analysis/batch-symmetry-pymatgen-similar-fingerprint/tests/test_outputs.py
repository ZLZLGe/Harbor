#!/usr/bin/env python3

import importlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


INPUT_DIR = Path("/root/structures")
OUTPUT_PATH = Path("/root/workspace/symmetry_fingerprint_report.json")
SYMPREC = 1e-3
ANGLE_TOLERANCE = 5

sys.path.insert(0, "/root/workspace")


def normalize_coord(value: float) -> float:
    normalized = float(value) % 1.0
    if abs(normalized - 1.0) < 5e-7 or abs(normalized) < 5e-7:
        normalized = 0.0
    return round(normalized, 6)


def species_summary(site) -> str:
    symbols = sorted({element.symbol for element in site.species.elements})
    return "-".join(symbols)


def summarize_structure(filepath: Path) -> dict[str, Any]:
    structure = Structure.from_file(filepath)
    analyzer = SpacegroupAnalyzer(
        structure,
        symprec=SYMPREC,
        angle_tolerance=ANGLE_TOLERANCE,
    )
    refined = analyzer.get_refined_structure(keep_site_properties=False)
    refined_analyzer = SpacegroupAnalyzer(
        refined,
        symprec=SYMPREC,
        angle_tolerance=ANGLE_TOLERANCE,
    )
    symmetrized = refined_analyzer.get_symmetrized_structure()

    wyckoff_representatives: dict[str, dict[str, Any]] = {}
    for wyckoff_symbol, equivalent_sites in zip(
        symmetrized.wyckoff_symbols,
        symmetrized.equivalent_sites,
    ):
        letter = wyckoff_symbol[-1]
        if letter in wyckoff_representatives:
            continue

        representative_site = equivalent_sites[0]
        wyckoff_representatives[letter] = {
            "species": species_summary(representative_site),
            "frac_coords": [
                normalize_coord(coord) for coord in representative_site.frac_coords
            ],
        }

    return {
        "space_group_number": refined_analyzer.get_space_group_number(),
        "crystal_system": refined_analyzer.get_crystal_system(),
        "equivalent_site_group_count": len(symmetrized.equivalent_sites),
        "wyckoff_representatives": dict(sorted(wyckoff_representatives.items())),
    }


def expected_report() -> dict[str, Any]:
    samples = {}
    for cif_path in sorted(INPUT_DIR.glob("*.cif")):
        samples[cif_path.name] = summarize_structure(cif_path)
    return {
        "input_directory": str(INPUT_DIR),
        "sample_count": len(samples),
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
    print("Testing batch symmetry fingerprint report")
    print("=" * 80)

    try:
        solution = importlib.import_module("solution")
        build_report = getattr(solution, "build_symmetry_fingerprint_report", None)
        assert callable(build_report), "build_symmetry_fingerprint_report is not callable"
        print("1. Entry function exists")
        passed_checks += 1
    except Exception as exc:
        print(f"1. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        actual_report = build_report(str(INPUT_DIR))
        assert isinstance(actual_report, dict), "returned report must be a dict"
        print("2. Function returns a dict report")
        passed_checks += 1
    except Exception as exc:
        print(f"2. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        expected = expected_report()
        assert actual_report == expected, (
            "returned report does not match expected symmetry fingerprint summary"
        )
        print("3. Returned report matches independent symmetry analysis")
        passed_checks += 1
    except Exception as exc:
        print(f"3. FAILED: {exc}")
        traceback.print_exc()

    try:
        assert OUTPUT_PATH.exists(), f"{OUTPUT_PATH} was not created"
        file_report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        assert file_report == actual_report, "JSON file content does not match function return value"
        print("4. JSON output file exists and matches the returned report")
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
