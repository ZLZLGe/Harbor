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


request = json.loads(Path("/root/data/transfer2_claims.json").read_text(encoding="utf-8"))
search = load_search()
reviews = []

for claim in request["claims"]:
    results = search(claim["city"])
    if isinstance(results, str):
        raise SystemExit(results)

    names = results["Name"].astype(str).str.strip()
    exact = results[names == claim["restaurant_name"].strip()].reset_index(drop=True)

    if exact.empty:
        reviews.append(
            {
                "claim_id": claim["claim_id"],
                "status": "rejected",
                "reasons": ["not_found"],
                "matched_restaurant": None,
                "average_cost": None,
                "aggregate_rating": None,
            }
        )
        continue

    row = exact.iloc[0]
    reasons = []
    if claim["required_cuisine"].lower() not in str(row["Cuisines"]).lower():
        reasons.append("cuisine_mismatch")
    if float(row["Average Cost"]) > float(claim["max_average_cost"]):
        reasons.append("cost_exceeded")
    if float(row["Aggregate Rating"]) < float(claim["min_aggregate_rating"]):
        reasons.append("rating_below_min")

    reviews.append(
        {
            "claim_id": claim["claim_id"],
            "status": "approved" if not reasons else "rejected",
            "reasons": reasons,
            "matched_restaurant": str(row["Name"]),
            "average_cost": float(row["Average Cost"]),
            "aggregate_rating": float(row["Aggregate Rating"]),
        }
    )

payload = {
    "batch_name": request["batch_name"],
    "approved_claim_ids": [item["claim_id"] for item in reviews if item["status"] == "approved"],
    "claim_reviews": reviews,
    "tool_called": ["search_restaurants"],
}

Path("/root/transfer2_claim_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
