#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from pathlib import Path

from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry


ENTRIES_PATH = Path("/root/phase_entries.json")
QUERIES_PATH = Path("/root/phase_queries.json")
OUTPUT_PATH = Path("/root/workspace/phase_hull_report.json")

sys.path.insert(0, "/root/workspace")


def round_float(value: float) -> float:
    value = float(value)
    if abs(value) < 5e-7:
        value = 0.0
    return round(value, 6)


def load_expected_report() -> dict:
    entries_payload = json.loads(ENTRIES_PATH.read_text(encoding="utf-8"))
    queries_payload = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))

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

    return {
        "entries_path": str(ENTRIES_PATH),
        "queries_path": str(QUERIES_PATH),
        "chemical_system": chemical_system,
        "entry_count": len(entry_records),
        "stable_entry_count": len(stable_entry_summaries),
        "stable_entry_ids": [item["entry_id"] for item in stable_entry_summaries],
        "stable_entries": stable_entry_summaries,
        "query_count": len(query_records),
        "query_results": query_results,
    }


def write_reward(score: float) -> None:
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")


def main() -> int:
    total_checks = 5
    passed_checks = 0

    print("=" * 80)
    print("Testing local phase hull stability analysis")
    print("=" * 80)

    try:
        solution = importlib.import_module("solution")
        build_report = getattr(solution, "build_phase_hull_report", None)
        assert callable(build_report), "build_phase_hull_report is not callable"
        print("1. Entry function exists")
        passed_checks += 1
    except Exception as exc:
        print(f"1. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        actual_report = build_report(str(ENTRIES_PATH), str(QUERIES_PATH))
        assert isinstance(actual_report, dict), "returned value must be a dict"
        print("2. Function returns a dict report")
        passed_checks += 1
    except Exception as exc:
        print(f"2. FAILED: {exc}")
        traceback.print_exc()
        write_reward(passed_checks / total_checks)
        return 0

    try:
        expected_report = load_expected_report()
        assert actual_report == expected_report, (
            "returned report does not match independent phase diagram analysis"
        )
        print("3. Returned report matches independent phase diagram analysis")
        passed_checks += 1
    except Exception as exc:
        print(f"3. FAILED: {exc}")
        traceback.print_exc()

    try:
        assert OUTPUT_PATH.exists(), f"{OUTPUT_PATH} was not created"
        file_report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        assert file_report == actual_report, (
            "JSON output file content does not match the returned report"
        )
        print("4. JSON output file exists and matches the returned report")
        passed_checks += 1
    except Exception as exc:
        print(f"4. FAILED: {exc}")
        traceback.print_exc()

    try:
        expected_text = json.dumps(actual_report, ensure_ascii=False, indent=2, sort_keys=True)
        actual_text = OUTPUT_PATH.read_text(encoding="utf-8").strip()
        assert actual_text == expected_text.strip(), (
            "JSON file formatting does not use indent=2 and sort_keys=True"
        )
        print("5. JSON file formatting matches indent=2 and sort_keys=True")
        passed_checks += 1
    except Exception as exc:
        print(f"5. FAILED: {exc}")
        traceback.print_exc()

    score = passed_checks / total_checks
    print("\nScore: {:.2f}".format(score))
    write_reward(score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
