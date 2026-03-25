#!/usr/bin/env python3
import json
from pathlib import Path


OUTPUT_PATH = Path("/root/similar_demographic_summary.json")
SOURCE_PATH = Path("/tests/fixtures/source.json")
QUARTILES = ["Q1", "Q2", "Q3", "Q4"]


def load_expected():
    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    rows.sort(key=lambda item: item["sa2_code"])
    ranked = sorted(rows, key=lambda item: (item["median_income"], item["sa2_code"]))
    total_rows = len(ranked)
    for index, row in enumerate(ranked):
        quartile_index = min((index * 4) // total_rows, 3)
        row["quartile"] = QUARTILES[quartile_index]
        row["total"] = row["earners"] * row["median_income"]

    by_code = {row["sa2_code"]: row for row in ranked}
    ordered = [by_code[row["sa2_code"]] for row in rows]
    states = sorted({row["state"] for row in ordered})

    population_totals = {state: 0 for state in states}
    earner_totals = {state: 0 for state in states}
    region_counts = {state: 0 for state in states}
    quartile_earners = {(state, quartile): 0 for state in states for quartile in QUARTILES}

    for row in ordered:
        state = row["state"]
        population_totals[state] += row["population_2024"]
        earner_totals[state] += row["earners"]
        region_counts[state] += 1
        quartile_earners[(state, row["quartile"])] += row["earners"]

    top_regions = sorted(ordered, key=lambda row: (-row["total"], row["sa2_code"]))[:3]

    return {
        "state_population_totals": [{"state": state, "population_2024": population_totals[state]} for state in states],
        "state_earner_totals": [{"state": state, "earners": earner_totals[state]} for state in states],
        "state_region_counts": [{"state": state, "region_count": region_counts[state]} for state in states],
        "state_income_quartile_earners": [
            {"state": state, "quartile": quartile, "earners": quartile_earners[(state, quartile)]}
            for state in states
            for quartile in QUARTILES
        ],
        "top_total_regions": [
            {
                "sa2_code": row["sa2_code"],
                "sa2_name": row["sa2_name"],
                "state": row["state"],
                "total": row["total"],
            }
            for row in top_regions
        ],
    }


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    actual = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = load_expected()

    assert list(actual.keys()) == list(expected.keys()), f"unexpected top-level keys: {list(actual.keys())}"
    assert actual == expected, "output JSON does not match expected demographic summary"


if __name__ == "__main__":
    main()
