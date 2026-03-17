#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


SUPPORTED_SUFFIXES = {".cif", ".vasp"}
SYMPREC = 1e-3
ANGLE_TOLERANCE = 5


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


def summarize_structure(structure: Structure) -> dict[str, float | int | str]:
    return {
        "formula": structure.composition.formula,
        "site_count": len(structure),
        "volume": round_float(structure.volume),
        "volume_per_atom": round_float(structure.volume / len(structure)),
    }


def build_sample_summary(path: Path) -> dict:
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


def build_normalization_manifest(
    input_dir: str,
    output_path: str = "/root/workspace/normalization_manifest.json",
) -> dict:
    input_path = Path(input_dir)
    sample_paths = sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )

    sample_order = [path.name for path in sample_paths]
    samples = {path.name: build_sample_summary(path) for path in sample_paths}
    manifest = {
        "input_directory": str(input_path),
        "sample_count": len(sample_paths),
        "sample_order": sample_order,
        "samples": samples,
    }

    output = Path(output_path)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest
EOF

chmod +x /root/workspace/solution.py
echo "Solution written to /root/workspace/solution.py"
