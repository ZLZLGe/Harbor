#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sys.path.insert(0, "/root/workspace")

from solution import cluster_structure_equivalence


INPUT_DIR = Path("/root/structure_exports")
MANIFEST_FILE = INPUT_DIR / "export_manifest.txt"
OUTPUT_FILE = Path("/root/workspace/structure_equivalence_clusters.json")


def load_manifest() -> list[str]:
    return [
        line.strip()
        for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines()
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


def expected_output() -> dict:
    manifest = load_manifest()
    structures = {name: load_structure(INPUT_DIR / name) for name in manifest}
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


def validate_schema(result: dict, manifest: list[str]) -> None:
    assert isinstance(result, dict)
    assert set(result.keys()) == {"input_file_count", "cluster_count", "clusters"}
    assert result["input_file_count"] == len(manifest)
    assert isinstance(result["cluster_count"], int)
    assert isinstance(result["clusters"], list)
    assert result["cluster_count"] == len(result["clusters"])

    seen_members = []
    previous_representative = None
    for cluster in result["clusters"]:
        assert isinstance(cluster, dict)
        assert set(cluster.keys()) == {
            "representative_file",
            "formula",
            "spacegroup_symbol",
            "spacegroup_number",
            "members",
        }
        assert isinstance(cluster["representative_file"], str) and cluster["representative_file"]
        assert isinstance(cluster["formula"], str) and cluster["formula"]
        assert isinstance(cluster["spacegroup_symbol"], str) and cluster["spacegroup_symbol"]
        assert isinstance(cluster["spacegroup_number"], int)
        assert isinstance(cluster["members"], list) and cluster["members"]
        assert cluster["members"] == sorted(cluster["members"])
        assert cluster["representative_file"] in cluster["members"]

        cif_members = sorted(name for name in cluster["members"] if name.lower().endswith(".cif"))
        expected_representative = cif_members[0] if cif_members else cluster["members"][0]
        assert cluster["representative_file"] == expected_representative

        if previous_representative is not None:
            assert previous_representative <= cluster["representative_file"]
        previous_representative = cluster["representative_file"]
        seen_members.extend(cluster["members"])

    assert sorted(seen_members) == sorted(manifest)
    assert len(seen_members) == len(manifest)


def main() -> int:
    manifest = load_manifest()
    function_result = cluster_structure_equivalence(str(INPUT_DIR))
    validate_schema(function_result, manifest)

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
