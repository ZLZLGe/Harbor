#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from pathlib import Path


def load_matrix():
    candidates = [
        Path("/root/.codex/skills/search-driving-distance/scripts"),
        Path("/root/.claude/skills/search-driving-distance/scripts"),
        Path("/app/skills/search-driving-distance/scripts"),
    ]
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))
    from search_driving_distance import GoogleDistanceMatrix

    return GoogleDistanceMatrix(path="/root/data/googleDistanceMatrix/distance.csv")


def fetch_leg(matrix, origin: str, destination: str) -> dict:
    info = matrix._lookup_local(origin, destination, "driving")
    if not info["duration"] or not info["distance"]:
        raise SystemExit(f"missing distance data for {origin} -> {destination}")
    duration = str(info["duration"])
    minutes = 0
    if "hour" in duration:
        hours_text = duration.split("hour", 1)[0].strip()
        minutes += int(hours_text) * 60
        remainder = duration.split("hour", 1)[1]
    else:
        remainder = duration
    if "min" in remainder:
        minute_text = remainder.split("min", 1)[0].replace("s", "").strip()
        if minute_text:
            minutes += int(minute_text)

    distance_text = str(info["distance"]).lower().replace("km", "").replace(",", "").strip()
    distance_km = round(float(distance_text), 1)
    return {
        "origin": origin,
        "destination": destination,
        "duration_minutes": minutes,
        "distance_km": distance_km,
        "estimated_cost": int(info["cost"]),
    }


request = json.loads(Path("/root/data/similar_route_candidates.json").read_text(encoding="utf-8"))
start_city = request["start_city"]
matrix = load_matrix()
route_summaries = []
recommended_legs = []
recommended_route_id = None
recommended_route_stops = None
best_key = None

for candidate in request["route_candidates"]:
    ordered_stops = list(candidate["cities"])
    full_route = [start_city, *ordered_stops, start_city]
    legs = []
    for index, (origin, destination) in enumerate(zip(full_route, full_route[1:]), start=1):
        leg = fetch_leg(matrix, origin, destination)
        leg["leg_number"] = index
        legs.append(leg)

    total_duration_minutes = sum(leg["duration_minutes"] for leg in legs)
    total_distance_km = round(sum(leg["distance_km"] for leg in legs), 1)
    total_estimated_cost = sum(leg["estimated_cost"] for leg in legs)
    route_summary = {
        "route_id": candidate["route_id"],
        "ordered_stops": ordered_stops,
        "total_duration_minutes": total_duration_minutes,
        "total_distance_km": total_distance_km,
        "total_estimated_cost": total_estimated_cost,
        "leg_count": len(legs),
    }
    route_summaries.append(route_summary)

    current_key = (total_duration_minutes, total_distance_km, candidate["route_id"])
    if best_key is None or current_key < best_key:
        best_key = current_key
        recommended_route_id = candidate["route_id"]
        recommended_route_stops = ordered_stops
        recommended_legs = legs

route_summaries.sort(key=lambda item: item["route_id"])

payload = {
    "start_city": start_city,
    "recommended_route_id": recommended_route_id,
    "recommended_route_stops": recommended_route_stops,
    "recommended_legs": recommended_legs,
    "route_summaries": route_summaries,
    "tool_called": ["search_driving_distance"],
}

Path("/root/similar_route_recommendation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
