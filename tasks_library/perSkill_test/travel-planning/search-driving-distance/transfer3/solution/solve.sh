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


def fetch_leg(matrix, origin: str, destination: str) -> tuple[int, float]:
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

    distance_km = round(float(str(info["distance"]).lower().replace("km", "").replace(",", "").strip()), 1)
    return minutes, distance_km


matrix = load_matrix()
request = json.loads(Path("/root/data/transfer3_roundtrip_lanes.json").read_text(encoding="utf-8"))
lane_rankings = []
for lane in request["lanes"]:
    outbound_duration, outbound_distance = fetch_leg(matrix, lane["city_a"], lane["city_b"])
    return_duration, return_distance = fetch_leg(matrix, lane["city_b"], lane["city_a"])
    lane_rankings.append(
        {
            "lane_id": lane["lane_id"],
            "city_a": lane["city_a"],
            "city_b": lane["city_b"],
            "outbound_duration_minutes": outbound_duration,
            "return_duration_minutes": return_duration,
            "duration_delta_minutes": abs(outbound_duration - return_duration),
            "outbound_distance_km": outbound_distance,
            "return_distance_km": return_distance,
            "distance_delta_km": round(abs(outbound_distance - return_distance), 1),
        }
    )

lane_rankings.sort(
    key=lambda item: (
        item["duration_delta_minutes"],
        item["distance_delta_km"],
        item["lane_id"],
    )
)

payload = {
    "most_balanced_lane_id": lane_rankings[0]["lane_id"],
    "lane_rankings": lane_rankings,
    "tool_called": ["search_driving_distance"],
}

Path("/root/transfer3_lane_balance_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
