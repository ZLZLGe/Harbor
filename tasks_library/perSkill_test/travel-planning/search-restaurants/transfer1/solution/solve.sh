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


request = json.loads(Path("/root/data/transfer1_host_request.json").read_text(encoding="utf-8"))
search = load_search()
summaries = []

for city in request["candidate_cities"]:
    results = search(city)
    if isinstance(results, str):
        raise SystemExit(results)

    bundle = []
    missing = []
    for cuisine in request["target_cuisines"]:
        filtered = results[
            results["Cuisines"].str.contains(cuisine, case=False, na=False)
            & (results["Average Cost"].astype(float) <= float(request["max_average_cost"]))
        ].copy()
        filtered = filtered.sort_values(
            by=["Average Cost", "Aggregate Rating", "Name"],
            ascending=[True, False, True],
        ).reset_index(drop=True)

        if filtered.empty:
            missing.append(cuisine)
            continue

        chosen = filtered.iloc[0]
        bundle.append(
            {
                "cuisine": cuisine,
                "restaurant_name": str(chosen["Name"]),
                "average_cost": float(chosen["Average Cost"]),
                "aggregate_rating": float(chosen["Aggregate Rating"]),
            }
        )

    summaries.append(
        {
            "city": city,
            "covered_cuisine_count": len(bundle),
            "missing_cuisines": missing,
            "estimated_bundle_cost": sum(item["average_cost"] for item in bundle),
            "bundle": bundle,
        }
    )

recommended = sorted(
    summaries,
    key=lambda item: (-item["covered_cuisine_count"], item["estimated_bundle_cost"], item["city"]),
)[0]["city"]

payload = {
    "brief_name": request["brief_name"],
    "recommended_city": recommended,
    "city_summaries": summaries,
    "tool_called": ["search_restaurants"],
}

Path("/root/transfer1_host_city_brief.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
