#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from pathlib import Path


def normalized_length(city: str) -> int:
    return len(city.replace(" ", ""))


def load_cities():
    candidates = [
        Path("/root/.codex/skills/search-cities/scripts"),
        Path("/root/.claude/skills/search-cities/scripts"),
        Path("/app/skills/search-cities/scripts"),
    ]
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))
    from search_cities import Cities

    return Cities().run


request = json.loads(Path("/root/data/similar_trip_request.json").read_text(encoding="utf-8"))
search = load_cities()
cities = search(request["state"])
if isinstance(cities, str):
    raise SystemExit(cities)

anchor_city = min((city for city in cities if city.startswith("C")), key=lambda city: city)
connector_city = max(
    (city for city in cities if "o" in city.lower()),
    key=lambda city: (normalized_length(city), city),
)
buffer_city = max(
    (city for city in cities if normalized_length(city) == 6),
    key=lambda city: city,
)

selected = [
    {
        "slot": "anchor_city",
        "rule": "alphabetically earliest city whose name starts with C",
        "city": anchor_city,
    },
    {
        "slot": "connector_city",
        "rule": "longest city name containing the letter o, ignoring spaces",
        "city": connector_city,
    },
    {
        "slot": "buffer_city",
        "rule": "alphabetically last city whose normalized name has exactly 6 letters",
        "city": buffer_city,
    },
]

route_order = sorted((entry["city"] for entry in selected), key=lambda city: (normalized_length(city), city))

payload = {
    "state": request["state"],
    "trip_days": request["trip_days"],
    "selected_cities": selected,
    "route_order": route_order,
    "tool_called": ["search_cities"],
}

Path("/root/similar_trip_city_shortlist.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
