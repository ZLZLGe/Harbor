#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3
import json
from pathlib import Path

from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


MANIFEST_NAME = "export_manifest.txt"
OUTPUT_NAME = "structure_equivalence_clusters.json"


def load_manifest(input_dir: Path) -> list[str]:
    manifest_path = input_dir / MANIFEST_NAME
    return [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_structure(path: Path) -> Structure:
    if path.suffix.lower() == ".cif":
        return Structure.from_file(path)
    return Poscar.from_file(path).structure


def choose_representative(members: list[str]) -> str:
    cif_members = sorted(name for name in members if name.lower().endswith(".cif"))
    if cif_members:
        return cif_members[0]
    return sorted(members)[0]


def cluster_structure_equivalence(input_dir: str) -> dict:
    base_dir = Path(input_dir)
    manifest = load_manifest(base_dir)
    structures = {name: load_structure(base_dir / name) for name in manifest}
    matcher = StructureMatcher(primitive_cell=True, scale=True, attempt_supercell=False)

    clusters = []
    assigned = set()
    for filename in manifest:
        if filename in assigned:
            continue

        group = [filename]
        assigned.add(filename)
        for candidate in manifest:
            if candidate in assigned:
                continue
            if matcher.fit(structures[filename], structures[candidate]):
                group.append(candidate)
                assigned.add(candidate)

        members = sorted(group)
        representative_file = choose_representative(members)
        representative_structure = structures[representative_file]
        analyzer = SpacegroupAnalyzer(representative_structure)
        clusters.append(
            {
                "representative_file": representative_file,
                "formula": representative_structure.composition.reduced_formula,
                "spacegroup_symbol": analyzer.get_space_group_symbol(),
                "spacegroup_number": analyzer.get_space_group_number(),
                "members": members,
            }
        )

    clusters.sort(key=lambda item: item["representative_file"])
    return {
        "input_file_count": len(manifest),
        "cluster_count": len(clusters),
        "clusters": clusters,
    }


if __name__ == "__main__":
    output = cluster_structure_equivalence("/root/structure_exports")
    Path("/root/workspace").mkdir(parents=True, exist_ok=True)
    Path("/root/workspace/structure_equivalence_clusters.json").write_text(
        json.dumps(output, indent=2, sort_keys=False),
        encoding="utf-8",
    )
EOF

chmod +x /root/workspace/solution.py
