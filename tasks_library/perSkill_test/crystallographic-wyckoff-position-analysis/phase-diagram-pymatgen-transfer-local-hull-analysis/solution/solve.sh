#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3
import csv
import json
from pathlib import Path

from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry


def _round_float(value: float) -> float:
    rounded = round(float(value), 6)
    if abs(rounded) < 5e-7:
        return 0.0
    return rounded


def _load_request(data_dir: str) -> dict:
    request_path = Path(data_dir) / "analysis_request.json"
    return json.loads(request_path.read_text(encoding="utf-8"))


def _load_entries(data_dir: str, chemical_system: list[str]) -> dict[str, ComputedEntry]:
    allowed_elements = set(chemical_system)
    entries_by_id: dict[str, ComputedEntry] = {}
    csv_path = Path(data_dir) / "entries.csv"

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            composition = Composition(row["formula"].strip())
            entry_elements = {element.symbol for element in composition.elements}
            if not entry_elements.issubset(allowed_elements):
                continue

            energy_per_atom = float(row["energy_per_atom"])
            entry = ComputedEntry(
                composition=composition,
                energy=energy_per_atom * composition.num_atoms,
                entry_id=row["entry_id"].strip(),
            )
            entries_by_id[entry.entry_id] = entry

    return entries_by_id


def _serialize_entry(entry: ComputedEntry) -> dict:
    return {
        "entry_id": entry.entry_id,
        "formula": entry.composition.reduced_formula,
        "energy_per_atom": _round_float(entry.energy_per_atom),
    }


def _serialize_target(entry: ComputedEntry, phase_diagram: PhaseDiagram) -> dict:
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
                    "amount": _round_float(amount),
                }
                for product_entry, amount in decomp_map.items()
            ],
            key=lambda item: (item["formula"], item["entry_id"]),
        )

    return {
        "entry_id": entry.entry_id,
        "formula": entry.composition.reduced_formula,
        "energy_per_atom": _round_float(entry.energy_per_atom),
        "is_stable": is_stable,
        "energy_above_hull": 0.0 if is_stable else _round_float(raw_energy_above_hull),
        "decomposition": decomposition,
    }


def build_local_phase_hull_report(data_dir: str) -> dict:
    request = _load_request(data_dir)
    chemical_system = request["chemical_system"]
    entries_by_id = _load_entries(data_dir, chemical_system)
    phase_diagram = PhaseDiagram(list(entries_by_id.values()))

    stable_entries = sorted(
        phase_diagram.stable_entries,
        key=lambda entry: (entry.composition.reduced_formula, entry.entry_id),
    )
    targets = [
        _serialize_target(entries_by_id[entry_id], phase_diagram)
        for entry_id in request["target_entry_ids"]
    ]

    return {
        "chemical_system": "-".join(chemical_system),
        "stable_entries": [_serialize_entry(entry) for entry in stable_entries],
        "targets": targets,
    }


if __name__ == "__main__":
    output = build_local_phase_hull_report("/root/local_phase_data")
    output_path = Path("/root/workspace/local_hull_analysis.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
EOF
