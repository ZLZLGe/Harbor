#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pymatgen.analysis.local_env import CrystalNN
from pymatgen.core import Structure


TOLERANCE = 1e-4
NN_FINDER = CrystalNN(
    distance_cutoffs=None,
    x_diff_weight=0.0,
    porous_adjustment=False,
)


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
        raise ValueError(f"expected exactly one site match, got {matches}")
    return matches[0]


def get_element_symbol(site) -> str:
    return site.species.elements[0].symbol


def build_neighbor_formula(neighbor_composition: dict[str, int]) -> str:
    return "-".join(f"{element}{count}" for element, count in sorted(neighbor_composition.items()))


def analyze_target(structure: Structure, label: str, target_frac_coords: list[float]) -> dict[str, Any]:
    site_index = locate_site_index(structure, target_frac_coords)
    center_site = structure[site_index]
    neighbor_info = NN_FINDER.get_nn_info(structure, site_index)

    neighbor_counter = Counter(get_element_symbol(item["site"]) for item in neighbor_info)
    neighbor_composition = dict(sorted(neighbor_counter.items()))

    distances = [
        round_float(structure.get_distance(site_index, item["site_index"], jimage=item["image"]))
        for item in neighbor_info
    ]
    if not distances:
        raise ValueError(f"no neighbors found for site {label}")

    min_distance = min(distances)
    max_distance = max(distances)
    center_element = get_element_symbol(center_site)
    neighbor_formula = build_neighbor_formula(neighbor_composition)
    coordination_number = len(neighbor_info)

    return {
        "label": label,
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


def build_coordination_signatures(
    structure_dir: str,
    target_spec_path: str,
    output_path: str = "/root/workspace/coordination_signatures.json",
) -> dict:
    structure_root = Path(structure_dir)
    target_spec = json.loads(Path(target_spec_path).read_text(encoding="utf-8"))
    sample_order = sorted(target_spec["samples"])

    samples: dict[str, Any] = {}
    for sample_name in sample_order:
        structure = Structure.from_file(structure_root / sample_name)
        targets = [
            analyze_target(
                structure=structure,
                label=target["label"],
                target_frac_coords=target["fractional_coords"],
            )
            for target in target_spec["samples"][sample_name]
        ]
        samples[sample_name] = {
            "formula": structure.composition.formula,
            "target_count": len(targets),
            "targets": targets,
        }

    manifest = {
        "structure_directory": str(structure_root),
        "target_spec_path": str(Path(target_spec_path)),
        "sample_count": len(sample_order),
        "sample_order": sample_order,
        "samples": samples,
    }

    output_file = Path(output_path)
    output_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    build_coordination_signatures(
        "/root/coordination_inputs",
        "/root/coordination_targets.json",
    )
PY

chmod +x /root/workspace/solution.py
python3 /root/workspace/solution.py
