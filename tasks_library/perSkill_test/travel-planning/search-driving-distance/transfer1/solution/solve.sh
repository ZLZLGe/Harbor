#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
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


def fetch_quote(matrix, origin: str, destination: str) -> tuple[int, float, int]:
    info = matrix._lookup_local(origin, destination, "taxi")
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
    return minutes, distance_km, int(info["cost"])


matrix = load_matrix()
input_path = Path("/root/data/transfer1_courier_requests.csv")
rows = []
with input_path.open(encoding="utf-8") as handle:
    for request in csv.DictReader(handle):
        duration_minutes, distance_km, taxi_quote = fetch_quote(matrix, request["origin"], request["destination"])
        rows.append(
            {
                "request_id": request["request_id"],
                "origin": request["origin"],
                "destination": request["destination"],
                "duration_minutes": duration_minutes,
                "distance_km": f"{distance_km:.1f}",
                "taxi_quote": taxi_quote,
                "within_budget": "yes" if taxi_quote <= int(request["max_taxi_budget"]) else "no",
            }
        )

rows.sort(key=lambda item: (item["taxi_quote"], item["request_id"]))
for index, row in enumerate(rows, start=1):
    row["rank_by_quote"] = index

output_path = Path("/root/transfer1_taxi_quote_sheet.csv")
with output_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "rank_by_quote",
            "request_id",
            "origin",
            "destination",
            "duration_minutes",
            "distance_km",
            "taxi_quote",
            "within_budget",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
