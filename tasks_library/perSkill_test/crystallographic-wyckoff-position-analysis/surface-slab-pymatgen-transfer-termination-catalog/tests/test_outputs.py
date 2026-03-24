#!/usr/bin/env python3
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from pymatgen.core import Composition, Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sys.path.insert(0, "/root/workspace")

from solution import build_slab_termination_catalog


INPUT_DIR = Path("/root/slab_catalog_inputs")
REQUEST_FILE = INPUT_DIR / "slab_requests.json"
OUTPUT_FILE = Path("/root/workspace/slab_termination_catalog.json")


def round_float(value: float) -> float:
    rounded = round(float(value), 6)
    if abs(rounded) < 5e-7:
        return 0.0
    return rounded


def load_request() -> dict:
    return json.loads(REQUEST_FILE.read_text(encoding="utf-8"))


def group_layers_by_z(slab, tol: float) -> list[list]:
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


def layer_formula(layer_sites: list) -> str:
    counts = Counter()
    for site in layer_sites:
        counts[site.specie.symbol] += 1
    return Composition(dict(counts)).reduced_formula


def summarize_bulk(bulk_request: dict, tol: float) -> dict:
    structure = Structure.from_file(INPUT_DIR / bulk_request["filename"])
    conventional = SpacegroupAnalyzer(structure).get_conventional_standard_structure()

    slabs = []
    for miller_index in bulk_request["miller_indices"]:
        generator = SlabGenerator(
            conventional,
            miller_index=tuple(miller_index),
            min_slab_size=bulk_request["min_slab_size"],
            min_vacuum_size=bulk_request["min_vacuum_size"],
            center_slab=True,
        )
        for slab in generator.get_slabs():
            layers = group_layers_by_z(slab, tol)
            bottom_layer = layer_formula(layers[0])
            top_layer = layer_formula(layers[-1])
            top_bottom_same = top_layer == bottom_layer
            slabs.append(
                {
                    "miller_index": list(miller_index),
                    "surface_area": round_float(slab.surface_area),
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
            )

    slabs.sort(
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
        "slab_count": len(slabs),
        "slabs": slabs,
    }


def expected_output() -> tuple[dict, dict]:
    request = load_request()
    tol = float(request["layer_merge_tol_angstrom"])
    bulks = [summarize_bulk(bulk_request, tol) for bulk_request in request["bulks"]]
    expected = {
        "bulk_count": len(bulks),
        "total_slab_count": sum(bulk["slab_count"] for bulk in bulks),
        "bulks": bulks,
    }
    return request, expected


def validate_schema(result: dict, request: dict) -> None:
    assert isinstance(result, dict)
    assert set(result.keys()) == {"bulk_count", "total_slab_count", "bulks"}
    assert result["bulk_count"] == len(request["bulks"])
    assert isinstance(result["total_slab_count"], int)
    assert isinstance(result["bulks"], list)
    assert len(result["bulks"]) == len(request["bulks"])

    running_total = 0
    for bulk_record, bulk_request in zip(result["bulks"], request["bulks"]):
        assert set(bulk_record.keys()) == {
            "bulk_id",
            "filename",
            "formula",
            "requested_miller_indices",
            "slab_count",
            "slabs",
        }
        assert bulk_record["bulk_id"] == bulk_request["bulk_id"]
        assert bulk_record["filename"] == bulk_request["filename"]
        assert bulk_record["requested_miller_indices"] == bulk_request["miller_indices"]
        assert isinstance(bulk_record["formula"], str) and bulk_record["formula"]
        assert isinstance(bulk_record["slab_count"], int)
        assert isinstance(bulk_record["slabs"], list)
        assert bulk_record["slab_count"] == len(bulk_record["slabs"])
        running_total += bulk_record["slab_count"]

        previous_sort_key = None
        for slab_record in bulk_record["slabs"]:
            assert set(slab_record.keys()) == {
                "miller_index",
                "surface_area",
                "layer_count",
                "termination_composition",
                "polarity_summary",
            }
            assert isinstance(slab_record["miller_index"], list)
            assert len(slab_record["miller_index"]) == 3
            assert all(isinstance(value, int) for value in slab_record["miller_index"])
            assert isinstance(slab_record["surface_area"], float)
            assert isinstance(slab_record["layer_count"], int)
            assert slab_record["layer_count"] > 0

            termination = slab_record["termination_composition"]
            assert set(termination.keys()) == {"top_layer", "bottom_layer"}
            assert isinstance(termination["top_layer"], str) and termination["top_layer"]
            assert isinstance(termination["bottom_layer"], str) and termination["bottom_layer"]

            polarity = slab_record["polarity_summary"]
            assert set(polarity.keys()) == {"top_bottom_same_composition", "termination_type"}
            assert isinstance(polarity["top_bottom_same_composition"], bool)
            assert polarity["termination_type"] in {"symmetric", "asymmetric"}
            assert (
                polarity["termination_type"] == "symmetric"
            ) == polarity["top_bottom_same_composition"]

            current_sort_key = (
                slab_record["miller_index"],
                termination["top_layer"],
                termination["bottom_layer"],
                slab_record["layer_count"],
                slab_record["surface_area"],
            )
            if previous_sort_key is not None:
                assert previous_sort_key <= current_sort_key
            previous_sort_key = current_sort_key

    assert result["total_slab_count"] == running_total


def main() -> int:
    request, expected = expected_output()

    function_result = build_slab_termination_catalog(str(INPUT_DIR))
    validate_schema(function_result, request)
    assert function_result == expected, f"Function output mismatch.\nExpected: {expected}\nGot: {function_result}"

    subprocess.run([sys.executable, "/root/workspace/solution.py"], check=True)
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
