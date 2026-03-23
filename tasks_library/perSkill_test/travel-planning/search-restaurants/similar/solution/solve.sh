#!/bin/bash
set -euo pipefail

python3 <<'PY'
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


request = json.loads(Path("/root/data/similar_trip_request.json").read_text(encoding="utf-8"))
search = load_search()
stops = []

for stop in request["stops"]:
    results = search(stop["city"])
    if isinstance(results, str):
        raise SystemExit(results)

    filtered = results[
        results["Cuisines"].str.contains(stop["requested_cuisine"], case=False, na=False)
        & (results["Average Cost"].astype(float) <= float(stop["max_average_cost"]))
        & (results["Aggregate Rating"].astype(float) >= float(stop["min_aggregate_rating"]))
    ].copy()

    if filtered.empty:
        raise SystemExit(f"No qualifying restaurant found for {stop['slot']}")

    filtered = filtered.sort_values(
        by=["Average Cost", "Aggregate Rating", "Name"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    chosen = filtered.iloc[0]
    stops.append(
        {
            "slot": stop["slot"],
            "city": stop["city"],
            "requested_cuisine": stop["requested_cuisine"],
            "restaurant_name": str(chosen["Name"]),
            "average_cost": float(chosen["Average Cost"]),
            "aggregate_rating": float(chosen["Aggregate Rating"]),
        }
    )

payload = {
    "trip_name": request["trip_name"],
    "stops": stops,
    "total_average_cost": sum(item["average_cost"] for item in stops),
    "tool_called": ["search_restaurants"],
}

Path("/root/similar_dining_route.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
