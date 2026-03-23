#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path


def load_flight_search():
    candidates = [
        Path("/root/.codex/skills/search-flights/scripts"),
        Path("/root/.claude/skills/search-flights/scripts"),
        Path("/app/skills/search-flights/scripts"),
    ]
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))
    from search_flights import Flights

    return Flights().run


def to_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def feasible_pairs(first_leg_result, second_leg_result, min_layover: int, max_layover: int):
    if isinstance(first_leg_result, str) or isinstance(second_leg_result, str):
        return []
    pairs = []
    for _, first in first_leg_result.iterrows():
        first_arrival = to_minutes(first["ArrTime"])
        for _, second in second_leg_result.iterrows():
            layover = to_minutes(second["DepTime"]) - first_arrival
            if min_layover <= layover <= max_layover:
                pairs.append(
                    {
                        "first_leg_flight_number": first["Flight Number"],
                        "second_leg_flight_number": second["Flight Number"],
                        "first_leg_departure": first["DepTime"],
                        "first_leg_arrival": first["ArrTime"],
                        "second_leg_departure": second["DepTime"],
                        "second_leg_arrival": second["ArrTime"],
                        "layover_minutes": int(layover),
                        "total_price": int(first["Price"] + second["Price"]),
                    }
                )
    pairs.sort(
        key=lambda pair: (
            pair["total_price"],
            pair["layover_minutes"],
            pair["first_leg_departure"],
            pair["first_leg_flight_number"],
            pair["second_leg_flight_number"],
        )
    )
    return pairs


request = json.loads(Path("/root/data/transfer3_connection_candidates.json").read_text(encoding="utf-8"))
search = load_flight_search()
summaries = []
for candidate in request["candidates"]:
    first_leg = candidate["first_leg"]
    second_leg = candidate["second_leg"]
    first_result = search(first_leg["origin"], first_leg["destination"], candidate["travel_date"])
    second_result = search(second_leg["origin"], second_leg["destination"], candidate["travel_date"])
    pairs = feasible_pairs(
        first_result,
        second_result,
        request["minimum_layover_minutes"],
        request["maximum_layover_minutes"],
    )
    summary = {
        "connection_id": candidate["connection_id"],
        "travel_date": candidate["travel_date"],
        "first_leg_route": f"{first_leg['origin']} -> {first_leg['destination']}",
        "second_leg_route": f"{second_leg['origin']} -> {second_leg['destination']}",
        "status": "FEASIBLE" if pairs else "NO_FEASIBLE_CONNECTION",
        "feasible_connection_count": len(pairs),
        "best_connection": pairs[0] if pairs else None,
    }
    summaries.append(summary)

eligible = [summary for summary in summaries if summary["best_connection"] is not None]
eligible.sort(
    key=lambda summary: (
        summary["best_connection"]["total_price"],
        summary["best_connection"]["layover_minutes"],
        summary["connection_id"],
    )
)

selected = None
if eligible:
    selected = {"connection_id": eligible[0]["connection_id"], **eligible[0]["best_connection"]}

payload = {
    "analysis_id": request["analysis_id"],
    "minimum_layover_minutes": request["minimum_layover_minutes"],
    "maximum_layover_minutes": request["maximum_layover_minutes"],
    "candidate_summaries": summaries,
    "selected_connection": selected,
    "tool_called": ["search_flights"],
}

Path("/root/transfer3_connection_screen.json").write_text(
    json.dumps(payload, indent=2),
    encoding="utf-8",
)
PY
