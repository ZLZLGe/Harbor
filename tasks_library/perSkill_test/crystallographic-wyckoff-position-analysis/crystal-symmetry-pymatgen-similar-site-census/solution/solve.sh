#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def _normalize_coord(value: float) -> float:
    normalized = float(value) % 1.0
    if abs(normalized) < 5e-7 or abs(normalized - 1.0) < 5e-7:
        normalized = 0.0
    normalized = round(normalized, 6)
    if normalized == 1.0:
        normalized = 0.0
    return normalized


def _load_manifest(cif_dir: str) -> list[str]:
    manifest_path = Path(cif_dir) / "batch_manifest.txt"
    return [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _summarize_structure(cif_path: Path) -> dict:
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
                    _normalize_coord(value) for value in representative.frac_coords
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


def build_symmetry_site_census(cif_dir: str) -> dict:
    base_dir = Path(cif_dir)
    filenames = _load_manifest(cif_dir)
    structures = [_summarize_structure(base_dir / filename) for filename in filenames]
    return {
        "processed_count": len(structures),
        "structures": structures,
    }


if __name__ == "__main__":
    output = build_symmetry_site_census("/root/census_inputs")
    output_path = Path("/root/workspace/symmetry_site_census.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
EOF

python3 /root/workspace/solution.py
