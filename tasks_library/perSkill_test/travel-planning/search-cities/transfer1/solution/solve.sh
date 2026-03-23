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


request = json.loads(Path("/root/data/transfer1_training_request.json").read_text(encoding="utf-8"))
search = load_cities()
cities = search(request["state"])
if isinstance(cities, str):
    raise SystemExit(cities)

two_word = [city for city in cities if " " in city]
max_two_word = max(normalized_length(city) for city in two_word)
campus_anchor = min((city for city in two_word if normalized_length(city) == max_two_word), key=lambda city: city)
drive_through_stop = min((city for city in cities if city.lower().endswith("o")), key=lambda city: (normalized_length(city), city))
coastal_gateway = min((city for city in cities if city.startswith("B")), key=lambda city: city)
selected_so_far = {campus_anchor, drive_through_stop, coastal_gateway}
backup_single_word = max(
    (city for city in cities if " " not in city and city not in selected_so_far),
    key=lambda city: (normalized_length(city), city),
)

selected = [
    {
        "slot": "campus_anchor",
        "rule": "alphabetically earliest two-word city among the longest two-word names",
        "city": campus_anchor,
    },
    {
        "slot": "drive_through_stop",
        "rule": "shortest city ending with the letter o",
        "city": drive_through_stop,
    },
    {
        "slot": "coastal_gateway",
        "rule": "alphabetically earliest city starting with B",
        "city": coastal_gateway,
    },
    {
        "slot": "backup_single_word",
        "rule": "longest remaining single-word city after the first three selections",
        "city": backup_single_word,
    },
]

rotation_order = sorted((entry["city"] for entry in selected), key=lambda city: (normalized_length(city), city))

payload = {
    "state": request["state"],
    "program": request["program"],
    "selected_cities": selected,
    "rotation_order": rotation_order,
    "tool_called": ["search_cities"],
}

Path("/root/transfer1_training_hubs.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
