#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from pathlib import Path


def normalized_length(city: str) -> int:
    return len(city.replace(" ", ""))


def word_count(city: str) -> int:
    return len(city.split())


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


request = json.loads(Path("/root/data/transfer3_outreach_request.json").read_text(encoding="utf-8"))
search = load_cities()
cities = search(request["state"])
if isinstance(cities, str):
    raise SystemExit(cities)

clinic_anchor = max((city for city in cities if " " not in city), key=lambda city: (normalized_length(city), city))
weekend_stop = min((city for city in cities if " " in city), key=lambda city: (normalized_length(city), city))
permit_city = min((city for city in cities if "City" in city.split()), key=lambda city: city)
comms_backup = max((city for city in cities if " " in city), key=lambda city: (normalized_length(city), city))

selected = [
    {
        "slot": "clinic_anchor",
        "rule": "longest single-word city",
        "city": clinic_anchor,
    },
    {
        "slot": "weekend_stop",
        "rule": "shortest multiword city",
        "city": weekend_stop,
    },
    {
        "slot": "permit_city",
        "rule": "alphabetically earliest city containing the word City",
        "city": permit_city,
    },
    {
        "slot": "comms_backup",
        "rule": "longest city name with a space",
        "city": comms_backup,
    },
]

visit_sequence = sorted((entry["city"] for entry in selected), key=lambda city: (-word_count(city), city))

payload = {
    "state": request["state"],
    "program": request["program"],
    "selected_cities": selected,
    "visit_sequence": visit_sequence,
    "tool_called": ["search_cities"],
}

Path("/root/transfer3_outreach_schedule.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
