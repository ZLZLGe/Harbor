#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path

from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry

sys.path.insert(0, "/root/workspace")

from solution import build_local_phase_hull_report


INPUT_DIR = Path("/root/local_phase_data")
ENTRIES_FILE = INPUT_DIR / "entries.csv"
REQUEST_FILE = INPUT_DIR / "analysis_request.json"
OUTPUT_FILE = Path("/root/workspace/local_hull_analysis.json")


def round_float(value: float) -> float:
    rounded = round(float(value), 6)
    if abs(rounded) < 5e-7:
        return 0.0
    return rounded


def load_request() -> dict:
    return json.loads(REQUEST_FILE.read_text(encoding="utf-8"))


def load_entries_for_system(chemical_system: list[str]) -> dict[str, ComputedEntry]:
    allowed_elements = set(chemical_system)
    entries_by_id: dict[str, ComputedEntry] = {}

    with ENTRIES_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            composition = Composition(row["formula"].strip())
            entry_elements = {element.symbol for element in composition.elements}
            if not entry_elements.issubset(allowed_elements):
                continue

            energy_per_atom = float(row["energy_per_atom"])
            entries_by_id[row["entry_id"].strip()] = ComputedEntry(
                composition=composition,
                energy=energy_per_atom * composition.num_atoms,
                entry_id=row["entry_id"].strip(),
            )

    return entries_by_id


def serialize_entry(entry: ComputedEntry) -> dict:
    return {
        "entry_id": entry.entry_id,
        "formula": entry.composition.reduced_formula,
        "energy_per_atom": round_float(entry.energy_per_atom),
    }


def expected_target_record(entry: ComputedEntry, phase_diagram: PhaseDiagram) -> dict:
    raw_energy_above_hull = float(phase_diagram.get_e_above_hull(entry))
    is_stable = abs(raw_energy_above_hull) < 5e-7

    decomposition = []
    if not is_stable:
        decomp_map, _ = phase_diagram.get_decomp_and_e_above_hull(entry)
        decomposition = sorted(
            [
                {
                    "entry_id": product_entry.entry_id,
                    "formula": product_entry.composition.reduced_formula,
                    "amount": round_float(amount),
                }
                for product_entry, amount in decomp_map.items()
            ],
            key=lambda item: (item["formula"], item["entry_id"]),
        )

    return {
        "entry_id": entry.entry_id,
        "formula": entry.composition.reduced_formula,
        "energy_per_atom": round_float(entry.energy_per_atom),
        "is_stable": is_stable,
        "energy_above_hull": 0.0 if is_stable else round_float(raw_energy_above_hull),
        "decomposition": decomposition,
    }


def build_reference() -> tuple[dict, list[dict], list[dict]]:
    request = load_request()
    entries_by_id = load_entries_for_system(request["chemical_system"])
    phase_diagram = PhaseDiagram(list(entries_by_id.values()))

    stable_entries = sorted(
        phase_diagram.stable_entries,
        key=lambda entry: (entry.composition.reduced_formula, entry.entry_id),
    )
    stable_records = [serialize_entry(entry) for entry in stable_entries]
    target_records = [
        expected_target_record(entries_by_id[entry_id], phase_diagram)
        for entry_id in request["target_entry_ids"]
    ]

    return request, stable_records, target_records


def validate_top_level(result: dict, request: dict) -> None:
    assert isinstance(result, dict)
    assert set(result.keys()) == {"chemical_system", "stable_entries", "targets"}
    assert result["chemical_system"] == "-".join(request["chemical_system"])
    assert isinstance(result["stable_entries"], list)
    assert isinstance(result["targets"], list)
    assert len(result["targets"]) == len(request["target_entry_ids"])


def validate_stable_entries(result: dict, expected_stable_entries: list[dict]) -> None:
    assert result["stable_entries"] == expected_stable_entries
    previous_key = None
    for record in result["stable_entries"]:
        assert set(record.keys()) == {"entry_id", "formula", "energy_per_atom"}
        assert isinstance(record["entry_id"], str) and record["entry_id"]
        assert isinstance(record["formula"], str) and record["formula"]
        assert isinstance(record["energy_per_atom"], float)
        current_key = (record["formula"], record["entry_id"])
        if previous_key is not None:
            assert previous_key <= current_key
        previous_key = current_key


def validate_targets(result: dict, request: dict, expected_targets: list[dict]) -> None:
    assert [record["entry_id"] for record in result["targets"]] == request["target_entry_ids"]

    for actual, expected in zip(result["targets"], expected_targets):
        assert actual == expected
        assert set(actual.keys()) == {
            "entry_id",
            "formula",
            "energy_per_atom",
            "is_stable",
            "energy_above_hull",
            "decomposition",
        }
        assert isinstance(actual["is_stable"], bool)
        assert isinstance(actual["energy_above_hull"], float)
        assert isinstance(actual["decomposition"], list)

        if actual["is_stable"]:
            assert actual["energy_above_hull"] == 0.0
            assert actual["decomposition"] == []
        else:
            previous_key = None
            for product in actual["decomposition"]:
                assert set(product.keys()) == {"entry_id", "formula", "amount"}
                assert isinstance(product["entry_id"], str) and product["entry_id"]
                assert isinstance(product["formula"], str) and product["formula"]
                assert isinstance(product["amount"], float)
                current_key = (product["formula"], product["entry_id"])
                if previous_key is not None:
                    assert previous_key <= current_key
                previous_key = current_key


def main() -> int:
    request, expected_stable_entries, expected_targets = build_reference()

    function_result = build_local_phase_hull_report(str(INPUT_DIR))
    validate_top_level(function_result, request)
    validate_stable_entries(function_result, expected_stable_entries)
    validate_targets(function_result, request, expected_targets)

    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    file_result = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    assert file_result == function_result, "Output file content does not match function result."

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
