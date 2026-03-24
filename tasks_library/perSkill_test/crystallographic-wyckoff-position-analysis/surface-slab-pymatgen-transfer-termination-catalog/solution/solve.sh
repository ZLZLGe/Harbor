#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

from pymatgen.core import Composition, Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


REQUEST_NAME = "slab_requests.json"
OUTPUT_NAME = "slab_termination_catalog.json"


def _round_float(value: float) -> float:
    rounded = round(float(value), 6)
    if abs(rounded) < 5e-7:
        return 0.0
    return rounded


def _load_request(data_dir: str) -> dict:
    request_path = Path(data_dir) / REQUEST_NAME
    return json.loads(request_path.read_text(encoding="utf-8"))


def _group_layers_by_z(slab, tol: float) -> list[list]:
    ordered_sites = sorted(slab, key=lambda site: float(site.coords[2]))
    layers: list[list] = []
    last_z = None

    for site in ordered_sites:
        current_z = float(site.coords[2])
        if last_z is None or current_z - last_z > tol:
            layers.append([site])
        else:
            layers[-1].append(site)
        last_z = current_z

    return layers


def _layer_formula(layer_sites: list) -> str:
    counts = Counter()
    for site in layer_sites:
        counts[site.specie.symbol] += 1
    return Composition(dict(counts)).reduced_formula


def _summarize_slab(slab, miller_index: list[int], tol: float) -> dict:
    layers = _group_layers_by_z(slab, tol)
    bottom_layer = _layer_formula(layers[0])
    top_layer = _layer_formula(layers[-1])
    top_bottom_same = top_layer == bottom_layer

    return {
        "miller_index": list(miller_index),
        "surface_area": _round_float(slab.surface_area),
        "layer_count": len(layers),
        "termination_composition": {
            "top_layer": top_layer,
            "bottom_layer": bottom_layer,
        },
        "polarity_summary": {
            "top_bottom_same_composition": top_bottom_same,
            "termination_type": "symmetric" if top_bottom_same else "asymmetric",
        },
    }


def _build_bulk_record(base_dir: Path, bulk_request: dict, tol: float) -> dict:
    structure = Structure.from_file(base_dir / bulk_request["filename"])
    conventional = SpacegroupAnalyzer(structure).get_conventional_standard_structure()

    slab_records = []
    for miller_index in bulk_request["miller_indices"]:
        generator = SlabGenerator(
            conventional,
            miller_index=tuple(miller_index),
            min_slab_size=bulk_request["min_slab_size"],
            min_vacuum_size=bulk_request["min_vacuum_size"],
            center_slab=True,
        )
        for slab in generator.get_slabs():
            slab_records.append(_summarize_slab(slab, miller_index, tol))

    slab_records.sort(
        key=lambda item: (
            item["miller_index"],
            item["termination_composition"]["top_layer"],
            item["termination_composition"]["bottom_layer"],
            item["layer_count"],
            item["surface_area"],
        )
    )

    return {
        "bulk_id": bulk_request["bulk_id"],
        "filename": bulk_request["filename"],
        "formula": conventional.composition.reduced_formula,
        "requested_miller_indices": [list(index) for index in bulk_request["miller_indices"]],
        "slab_count": len(slab_records),
        "slabs": slab_records,
    }


def build_slab_termination_catalog(data_dir: str) -> dict:
    base_dir = Path(data_dir)
    request = _load_request(data_dir)
    tol = float(request["layer_merge_tol_angstrom"])

    bulks = [
        _build_bulk_record(base_dir, bulk_request, tol)
        for bulk_request in request["bulks"]
    ]

    return {
        "bulk_count": len(bulks),
        "total_slab_count": sum(bulk["slab_count"] for bulk in bulks),
        "bulks": bulks,
    }


if __name__ == "__main__":
    output = build_slab_termination_catalog("/root/slab_catalog_inputs")
    output_path = Path("/root/workspace") / OUTPUT_NAME
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
EOF

chmod +x /root/workspace/solution.py
