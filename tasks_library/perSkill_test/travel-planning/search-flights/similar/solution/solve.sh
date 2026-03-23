#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
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


def choose_cheapest(result):
    if isinstance(result, str):
        return None
    ordered = result.sort_values(["Price", "DepTime", "Flight Number"]).reset_index(drop=True)
    row = ordered.iloc[0]
    return {
        "origin": row["OriginCityName"],
        "destination": row["DestCityName"],
        "flight_date": row["FlightDate"],
        "flight_number": row["Flight Number"],
        "price": int(row["Price"]),
        "departure_time": row["DepTime"],
        "arrival_time": row["ArrTime"],
    }


request = json.loads(Path("/root/data/similar_roundtrip_requests.json").read_text(encoding="utf-8"))
search = load_flight_search()
evaluated = []

for candidate in request["candidates"]:
    outbound = candidate["outbound"]
    returning = candidate["return"]
    outbound_pick = choose_cheapest(
        search(outbound["origin"], outbound["destination"], outbound["flight_date"])
    )
    return_pick = choose_cheapest(
        search(returning["origin"], returning["destination"], returning["flight_date"])
    )
    available = outbound_pick is not None and return_pick is not None
    total_price = (
        outbound_pick["price"] + return_pick["price"]
        if available
        else None
    )
    evaluated.append(
        {
            "option_id": candidate["option_id"],
            "route_label": candidate["route_label"],
            "available": available,
            "outbound": outbound_pick if available else None,
            "return": return_pick if available else None,
            "total_price": total_price,
        }
    )

eligible = [
    option
    for option in evaluated
    if option["available"] and option["total_price"] <= request["budget_cap"]
]
eligible.sort(
    key=lambda option: (
        option["total_price"],
        option["outbound"]["departure_time"],
        option["option_id"],
    )
)

payload = {
    "request_id": request["request_id"],
    "budget_cap": request["budget_cap"],
    "evaluated_options": evaluated,
    "selected_option": eligible[0] if eligible else None,
    "tool_called": ["search_flights"],
}

Path("/root/similar_roundtrip_brief.json").write_text(
    json.dumps(payload, indent=2),
    encoding="utf-8",
)
PY
