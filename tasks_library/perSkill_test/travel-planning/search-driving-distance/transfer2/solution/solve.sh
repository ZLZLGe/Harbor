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


def fetch_duration(matrix, origin: str, destination: str) -> int:
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
    return minutes


matrix = load_matrix()
feasible = []
infeasible = []
with Path("/root/data/transfer2_site_hops.tsv").open(encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        duration_minutes = fetch_duration(matrix, row["origin"], row["destination"])
        margin = int(row["max_duration_minutes"]) - duration_minutes
        entry = {
            "lane_id": row["lane_id"],
            "origin": row["origin"],
            "destination": row["destination"],
            "duration_minutes": duration_minutes,
            "margin": margin,
        }
        if margin >= 0:
            feasible.append(entry)
        else:
            infeasible.append(entry)

feasible.sort(key=lambda item: (-item["margin"], item["lane_id"]))
infeasible.sort(key=lambda item: (abs(item["margin"]), item["lane_id"]))

lines = ["# Southeast Site-Hop Feasibility", "", "## Feasible"]
for item in feasible:
    lines.append(
        f"- {item['lane_id']} | {item['origin']} -> {item['destination']} | "
        f"{item['duration_minutes']} min | margin +{item['margin']}"
    )

lines.extend(["", "## Infeasible"])
for item in infeasible:
    lines.append(
        f"- {item['lane_id']} | {item['origin']} -> {item['destination']} | "
        f"{item['duration_minutes']} min | margin {item['margin']}"
    )

lines.extend(
    [
        "",
        f"feasible_count: {len(feasible)}",
        f"infeasible_count: {len(infeasible)}",
        "tool_called: search_driving_distance",
    ]
)

Path("/root/transfer2_site_hop_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
