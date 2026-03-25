#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import sys
from pathlib import Path


def load_search():
    candidates = [
        Path("/root/.codex/skills/search-restaurants/scripts"),
        Path("/root/.claude/skills/search-restaurants/scripts"),
        Path("/app/skills/search-restaurants/scripts"),
    ]
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))
    from search_restaurants import Restaurants

    return Restaurants().run


request = json.loads(Path("/root/data/transfer3_matrix_request.json").read_text(encoding="utf-8"))
search = load_search()
rows = []

for city in request["cities"]:
    results = search(city)
    if isinstance(results, str):
        raise SystemExit(results)

    for cuisine in request["cuisines"]:
        filtered = results[results["Cuisines"].str.contains(cuisine, case=False, na=False)].copy()
        if filtered.empty:
            raise SystemExit(f"No rows found for {city} / {cuisine}")

        cheapest = filtered.sort_values(
            by=["Average Cost", "Aggregate Rating", "Name"],
            ascending=[True, False, True],
        ).reset_index(drop=True).iloc[0]
        highest = filtered.sort_values(
            by=["Aggregate Rating", "Average Cost", "Name"],
            ascending=[False, True, True],
        ).reset_index(drop=True).iloc[0]

        rows.append(
            {
                "city": city,
                "requested_cuisine": cuisine,
                "match_count": int(len(filtered)),
                "cheapest_restaurant": str(cheapest["Name"]),
                "cheapest_cost": float(cheapest["Average Cost"]),
                "highest_rated_restaurant": str(highest["Name"]),
                "highest_rating": float(highest["Aggregate Rating"]),
            }
        )

fieldnames = [
    "city",
    "requested_cuisine",
    "match_count",
    "cheapest_restaurant",
    "cheapest_cost",
    "highest_rated_restaurant",
    "highest_rating",
]

with Path("/root/transfer3_cuisine_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
