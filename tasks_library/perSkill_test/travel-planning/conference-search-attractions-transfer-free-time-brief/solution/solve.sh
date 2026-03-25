#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
import json
import sys
from pathlib import Path

APP_ROOT = Path(__import__("os").environ.get("APP_ROOT", "/app"))
sys.path.append(str(APP_ROOT / "skills" / "search-attractions" / "scripts"))

from search_attractions import Attractions


CITY_PATH = APP_ROOT / "data" / "conference_cities.csv"
SLOT_PATH = APP_ROOT / "data" / "free_time_slots.json"
ATTRACTIONS_PATH = APP_ROOT / "data" / "attractions" / "attractions.csv"
OUTPUT_PATH = APP_ROOT / "output" / "conference_free_time_brief.md"


def load_cities():
    with CITY_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_slots():
    with SLOT_PATH.open() as handle:
        payload = json.load(handle)
    return payload["slots"]


def choose_items(city, count, engine):
    result = engine.run(city)
    if isinstance(result, str):
        raise SystemExit(f"Unable to load attractions for {city}: {result}")
    rows = (
        result[["Name", "Address", "Website"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return rows


def main():
    cities = load_cities()
    slots = load_slots()
    engine = Attractions(path=ATTRACTIONS_PATH)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Conference Free-Time City Brief", ""]

    required_total = sum(slot["count"] for slot in slots)

    for city_row in cities:
        city = city_row["city"]
        rows = choose_items(city, required_total, engine)
        if len(rows) < required_total:
            raise SystemExit(f"Not enough attractions for {city}.")

        lines.append(f"## {city}")
        lines.append("")

        cursor = 0
        for slot in slots:
            lines.append(f"### {slot['slot']}")
            chunk = rows.iloc[cursor : cursor + slot["count"]]
            for _, entry in chunk.iterrows():
                lines.append(
                    f"- {entry['Name']} | {entry['Address']} | {entry['Website']}"
                )
            lines.append("")
            cursor += slot["count"]

    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    main()
PY
