#!/bin/bash

set -euo pipefail

export OUTPUT_PATH="${OUTPUT_PATH:-/app/output/city_break_guide.json}"
export REQUEST_PATH="${REQUEST_PATH:-/app/data/city_break_request.json}"

python3 <<'PY'
import json
import sys
from pathlib import Path


request_path = Path(__import__("os").environ["REQUEST_PATH"])
output_path = Path(__import__("os").environ["OUTPUT_PATH"])
base_dir = Path.cwd()

skill_roots = [
    Path("/app/skills"),
    base_dir / "environment" / "skills",
    base_dir / "skills",
]
for root in skill_roots:
    skill_path = root / "search-attractions" / "scripts"
    if skill_path.exists():
        sys.path.append(str(skill_path))

from search_attractions import Attractions


def to_entry(row):
    return {
        "name": row["Name"],
        "address": row["Address"],
        "website": row["Website"],
    }


with request_path.open() as f:
    request = json.load(f)

data_candidates = [
    Path("/app/data/attractions/attractions.csv"),
    base_dir / "environment" / "data" / "attractions" / "attractions.csv",
    base_dir / "data" / "attractions" / "attractions.csv",
]
data_path = next((path for path in data_candidates if path.exists()), None)
if data_path is None:
    raise FileNotFoundError("Attractions CSV not found.")

selector = request["selection_rules"]
block_sizes = [
    ("morning_attractions", selector["morning_count"]),
    ("afternoon_attractions", selector["afternoon_count"]),
    ("evening_attractions", selector["evening_count"]),
]
needed_per_day = sum(size for _, size in block_sizes)

attractions = Attractions(path=data_path)
days = []
day_number = 1

for stop in request["city_stays"]:
    city = stop["city"]
    results = attractions.run(city)
    if isinstance(results, str):
        raise RuntimeError(results)
    results = results.sort_values(["Name", "Address"]).reset_index(drop=True)

    required_rows = stop["days"] * needed_per_day
    if len(results) < required_rows:
        raise RuntimeError(f"{city} does not have enough attractions for the requested guide.")

    cursor = 0
    for offset in range(stop["days"]):
        focus_keyword = stop["focus_keywords"][offset % len(stop["focus_keywords"])]
        day_payload = {
            "day": day_number,
            "current_city": city,
            "focus": f"{focus_keyword} city break",
        }
        for field, size in block_sizes:
            chunk = results.iloc[cursor:cursor + size]
            cursor += size
            day_payload[field] = [to_entry(row) for _, row in chunk.iterrows()]
        days.append(day_payload)
        day_number += 1

payload = {
    "trip_name": request["trip_name"],
    "days": days,
}

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w") as f:
    json.dump(payload, f, indent=2)
PY
