#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sys.path.insert(0, "/root/workspace")

from solution import build_symmetry_site_census


INPUT_DIR = Path("/root/census_inputs")
OUTPUT_FILE = Path("/root/workspace/symmetry_site_census.json")
MANIFEST_FILE = INPUT_DIR / "batch_manifest.txt"


def normalize_coord(value: float) -> float:
    normalized = float(value) % 1.0
    if abs(normalized) < 5e-7 or abs(normalized - 1.0) < 5e-7:
        normalized = 0.0
    normalized = round(normalized, 6)
    if normalized == 1.0:
        normalized = 0.0
    return normalized


def load_manifest() -> list[str]:
    return [
        line.strip()
        for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_structure(cif_path: Path) -> dict:
    structure = Structure.from_file(cif_path)
    analyzer = SpacegroupAnalyzer(structure)
    symmetrized = analyzer.get_symmetrized_structure()

    grouped_by_element = defaultdict(list)
    for equivalent_sites, wyckoff_symbol in zip(
        symmetrized.equivalent_sites, symmetrized.wyckoff_symbols
    ):
        representative = equivalent_sites[0]
        element = representative.specie.symbol
        grouped_by_element[element].append(
            {
                "wyckoff_letter": wyckoff_symbol[-1],
                "representative_frac_coords": [
                    normalize_coord(value) for value in representative.frac_coords
                ],
            }
        )

    element_site_summary = {}
    for element, groups in sorted(grouped_by_element.items()):
        sorted_groups = sorted(
            groups,
            key=lambda item: (
                item["wyckoff_letter"],
                item["representative_frac_coords"],
            ),
        )
        element_site_summary[element] = {
            "equivalent_group_count": len(sorted_groups),
            "groups": sorted_groups,
        }

    return {
        "filename": cif_path.name,
        "formula": structure.composition.reduced_formula,
        "spacegroup_symbol": analyzer.get_space_group_symbol(),
        "spacegroup_number": analyzer.get_space_group_number(),
        "crystal_system": analyzer.get_crystal_system(),
        "element_site_summary": element_site_summary,
    }


def expected_output() -> dict:
    filenames = load_manifest()
    structures = [summarize_structure(INPUT_DIR / filename) for filename in filenames]
    return {
        "processed_count": len(structures),
        "structures": structures,
    }


def validate_schema(result: dict, manifest_filenames: list[str]) -> None:
    assert isinstance(result, dict)
    assert set(result.keys()) == {"processed_count", "structures"}
    assert result["processed_count"] == len(manifest_filenames)
    assert isinstance(result["structures"], list)
    assert len(result["structures"]) == len(manifest_filenames)

    for structure_record, expected_filename in zip(result["structures"], manifest_filenames):
        assert isinstance(structure_record, dict)
        assert structure_record["filename"] == expected_filename
        assert isinstance(structure_record["formula"], str) and structure_record["formula"]
        assert isinstance(structure_record["spacegroup_symbol"], str) and structure_record["spacegroup_symbol"]
        assert isinstance(structure_record["spacegroup_number"], int)
        assert isinstance(structure_record["crystal_system"], str) and structure_record["crystal_system"]

        element_summary = structure_record["element_site_summary"]
        assert isinstance(element_summary, dict) and element_summary

        for element, element_record in element_summary.items():
            assert isinstance(element, str) and element
            assert isinstance(element_record, dict)
            assert set(element_record.keys()) == {"equivalent_group_count", "groups"}
            assert isinstance(element_record["equivalent_group_count"], int)
            assert isinstance(element_record["groups"], list)
            assert element_record["equivalent_group_count"] == len(element_record["groups"])

            for group in element_record["groups"]:
                assert isinstance(group, dict)
                assert set(group.keys()) == {"wyckoff_letter", "representative_frac_coords"}
                assert isinstance(group["wyckoff_letter"], str) and len(group["wyckoff_letter"]) == 1
                coords = group["representative_frac_coords"]
                assert isinstance(coords, list) and len(coords) == 3
                for value in coords:
                    assert isinstance(value, float)
                    assert 0.0 <= value < 1.0 or value == 0.0


def main() -> int:
    manifest_filenames = load_manifest()
    function_result = build_symmetry_site_census(str(INPUT_DIR))
    validate_schema(function_result, manifest_filenames)

    expected = expected_output()
    assert function_result == expected, f"Function output mismatch.\nExpected: {expected}\nGot: {function_result}"

    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    file_result = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    assert file_result == expected, f"Output file mismatch.\nExpected: {expected}\nGot: {file_result}"

    Path("/logs/verifier").mkdir(parents=True, exist_ok=True)
    Path("/logs/verifier/reward.txt").write_text("1.00\n", encoding="utf-8")
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        Path("/logs/verifier").mkdir(parents=True, exist_ok=True)
        Path("/logs/verifier/reward.txt").write_text("0.00\n", encoding="utf-8")
        print(exc)
        raise
