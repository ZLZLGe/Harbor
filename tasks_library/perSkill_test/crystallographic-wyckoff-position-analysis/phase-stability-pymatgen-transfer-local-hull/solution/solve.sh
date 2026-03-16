#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/solution.py <<'EOF'
#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry


def round_float(value: float) -> float:
    value = float(value)
    if abs(value) < 5e-7:
        value = 0.0
    return round(value, 6)


def build_phase_hull_report(
    entries_path: str,
    queries_path: str,
    output_path: str = "/root/workspace/phase_hull_report.json",
) -> dict:
    entries_payload = json.loads(Path(entries_path).read_text(encoding="utf-8"))
    queries_payload = json.loads(Path(queries_path).read_text(encoding="utf-8"))

    entry_records = entries_payload["entries"]
    query_records = queries_payload["queries"]

    entry_lookup: dict[int, dict] = {}
    computed_entries = []

    for record in entry_records:
        composition = Composition(record["formula"])
        entry = ComputedEntry(composition, float(record["energy"]), entry_id=record["entry_id"])
        computed_entries.append(entry)
        entry_lookup[id(entry)] = {
            "entry_id": record["entry_id"],
            "formula": record["formula"],
            "reduced_formula": composition.reduced_formula,
        }

    phase_diagram = PhaseDiagram(computed_entries)

    def entry_sort_key(entry: ComputedEntry) -> tuple[str, str]:
        metadata = entry_lookup[id(entry)]
        return (metadata["reduced_formula"], metadata["entry_id"])

    stable_entries = sorted(phase_diagram.stable_entries, key=entry_sort_key)

    stable_entry_summaries = []
    for entry in stable_entries:
        metadata = entry_lookup[id(entry)]
        stable_entry_summaries.append(
            {
                "entry_id": metadata["entry_id"],
                "formula": metadata["formula"],
                "reduced_formula": metadata["reduced_formula"],
                "energy": round_float(entry.energy),
                "energy_per_atom": round_float(entry.energy_per_atom),
            }
        )

    query_results = []
    for record in query_records:
        composition = Composition(record["formula"])
        query_entry = ComputedEntry(
            composition,
            float(record["energy"]),
            entry_id=record["query_id"],
        )
        decomposition, energy_above_hull = phase_diagram.get_decomp_and_e_above_hull(query_entry)
        ordered_decomposition = sorted(decomposition.items(), key=lambda item: entry_sort_key(item[0]))

        energy_above_hull = round_float(energy_above_hull)
        energy_per_atom = round_float(query_entry.energy_per_atom)
        hull_energy_per_atom = round_float(query_entry.energy_per_atom - energy_above_hull)

        query_results.append(
            {
                "query_id": record["query_id"],
                "formula": record["formula"],
                "reduced_formula": composition.reduced_formula,
                "energy": round_float(query_entry.energy),
                "energy_per_atom": energy_per_atom,
                "energy_above_hull": energy_above_hull,
                "hull_energy_per_atom": hull_energy_per_atom,
                "is_stable": energy_above_hull <= 1e-6,
                "decomposition": [
                    {
                        "entry_id": entry_lookup[id(entry)]["entry_id"],
                        "formula": entry_lookup[id(entry)]["formula"],
                        "reduced_formula": entry_lookup[id(entry)]["reduced_formula"],
                        "amount": round_float(amount),
                    }
                    for entry, amount in ordered_decomposition
                ],
            }
        )

    chemical_system = "-".join(
        sorted(
            {
                element.symbol
                for record in entry_records
                for element in Composition(record["formula"]).elements
            }
        )
    )

    report = {
        "entries_path": entries_path,
        "queries_path": queries_path,
        "chemical_system": chemical_system,
        "entry_count": len(entry_records),
        "stable_entry_count": len(stable_entry_summaries),
        "stable_entry_ids": [item["entry_id"] for item in stable_entry_summaries],
        "stable_entries": stable_entry_summaries,
        "query_count": len(query_records),
        "query_results": query_results,
    }

    Path(output_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    build_phase_hull_report("/root/phase_entries.json", "/root/phase_queries.json")
EOF

echo "Solution written to /root/workspace/solution.py"
