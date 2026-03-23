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


request = json.loads(Path("/root/data/transfer2_coverage_request.json").read_text(encoding="utf-8"))
search = load_cities()
cities = search(request["state"])
if isinstance(cities, str):
    raise SystemExit(cities)

san_lane = min((city for city in cities if city.startswith("San ")), key=lambda city: city)
santa_lane = max((city for city in cities if city.startswith("Santa ")), key=lambda city: city)
oak_lane = min(
    (city for city in cities if " " not in city and "k" in city.lower()),
    key=lambda city: (normalized_length(city), city),
)
southern_backup = min((city for city in cities if " " in city and city.startswith("L")), key=lambda city: city)

selected = [
    {
        "slot": "san_lane",
        "rule": "alphabetically earliest city starting with San",
        "city": san_lane,
    },
    {
        "slot": "santa_lane",
        "rule": "alphabetically latest city starting with Santa",
        "city": santa_lane,
    },
    {
        "slot": "oak_lane",
        "rule": "shortest single-word city containing the letter k",
        "city": oak_lane,
    },
    {
        "slot": "southern_backup",
        "rule": "alphabetically earliest multiword city starting with L",
        "city": southern_backup,
    },
]

inspection_order = sorted((entry["city"] for entry in selected), key=lambda city: (normalized_length(city), city))

payload = {
    "state": request["state"],
    "mission": request["mission"],
    "selected_cities": selected,
    "inspection_order": inspection_order,
    "tool_called": ["search_cities"],
}

Path("/root/transfer2_service_coverage.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
