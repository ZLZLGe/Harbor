#!/bin/bash
set -e

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Any

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


DEFAULT_OUTPUT_PATH = "/root/workspace/symmetry_fingerprint_report.json"
SYMPREC = 1e-3
ANGLE_TOLERANCE = 5


def _normalize_coord(value: float) -> float:
    normalized = float(value) % 1.0
    if abs(normalized - 1.0) < 5e-7 or abs(normalized) < 5e-7:
        normalized = 0.0
    return round(normalized, 6)


def _species_summary(site) -> str:
    symbols = sorted({element.symbol for element in site.species.elements})
    return "-".join(symbols)


def _summarize_structure(filepath: Path) -> dict[str, Any]:
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
            "species": _species_summary(representative_site),
            "frac_coords": [
                _normalize_coord(coord) for coord in representative_site.frac_coords
            ],
        }

    return {
        "space_group_number": refined_analyzer.get_space_group_number(),
        "crystal_system": refined_analyzer.get_crystal_system(),
        "equivalent_site_group_count": len(symmetrized.equivalent_sites),
        "wyckoff_representatives": dict(sorted(wyckoff_representatives.items())),
    }


def build_symmetry_fingerprint_report(
    input_dir: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    samples = {}

    for cif_path in sorted(input_path.glob("*.cif")):
        samples[cif_path.name] = _summarize_structure(cif_path)

    report = {
        "input_directory": str(input_path),
        "sample_count": len(samples),
        "samples": samples,
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    build_symmetry_fingerprint_report("/root/structures")
PY

echo "Solution written to /root/workspace/solution.py"
