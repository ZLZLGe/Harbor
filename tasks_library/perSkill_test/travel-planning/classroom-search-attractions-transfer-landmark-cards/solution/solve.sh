#!/bin/bash

set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"

mkdir -p "$APP_ROOT/output"

python3 <<'PY'
import csv
import json
import os
import sys
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
CITY_PATH = APP_ROOT / "data" / "classroom_cities.txt"
TEMPLATE_PATH = APP_ROOT / "data" / "card_export_template.json"
ATTRACTIONS_PATH = APP_ROOT / "data" / "attractions" / "attractions.csv"
OUTPUT_PATH = APP_ROOT / "output" / "landmark_cards.csv"
SKILL_PATH = APP_ROOT / "skills" / "search-attractions" / "scripts"

sys.path.append(str(SKILL_PATH))
from search_attractions import Attractions


def load_cities():
    return [line.strip() for line in CITY_PATH.read_text().splitlines() if line.strip()]


def load_template():
    with TEMPLATE_PATH.open() as handle:
        return json.load(handle)


template = load_template()
cities = load_cities()
groups = [item["card_group"] for item in template["card_groups"]]
searcher = Attractions(path=ATTRACTIONS_PATH)
rows = []

for city in cities:
    results = searcher.run(city)
    if isinstance(results, str):
        raise RuntimeError(f"Missing attractions for {city}: {results}")

    used_names = set()
    selected = []
    for _, row in results.iterrows():
        name = str(row["Name"])
        if name in used_names:
            continue
        selected.append(
            {
                "attraction_name": name,
                "address": str(row["Address"]),
                "website": str(row["Website"]),
            }
        )
        used_names.add(name)
        if len(selected) == len(groups):
            break

    if len(selected) != len(groups):
        raise RuntimeError(f"Not enough unique attractions for {city}")

    for group, item in zip(groups, selected):
        rows.append(
            {
                "city": city,
                "card_group": group,
                "attraction_name": item["attraction_name"],
                "address": item["address"],
                "website": item["website"],
            }
        )

with OUTPUT_PATH.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=template["columns"])
    writer.writeheader()
    writer.writerows(rows)
PY
