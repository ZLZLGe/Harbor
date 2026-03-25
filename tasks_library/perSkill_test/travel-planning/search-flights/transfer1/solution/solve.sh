#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
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
        "selected_flight_number": row["Flight Number"],
        "selected_price": str(int(row["Price"])),
        "selected_departure": row["DepTime"],
        "selected_arrival": row["ArrTime"],
    }


search = load_flight_search()
request_path = Path("/root/data/transfer1_manifest_requests.csv")
output_path = Path("/root/transfer1_manifest.csv")

with request_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

fieldnames = [
    "request_id",
    "priority",
    "status",
    "origin",
    "destination",
    "flight_date",
    "selected_flight_number",
    "selected_price",
    "selected_departure",
    "selected_arrival",
    "tool_called",
]

with output_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        result = search(row["origin"], row["destination"], row["flight_date"])
        chosen = choose_cheapest(result)
        writer.writerow(
            {
                "request_id": row["request_id"],
                "priority": row["priority"],
                "status": "AVAILABLE" if chosen else "NO_SERVICE",
                "origin": row["origin"],
                "destination": row["destination"],
                "flight_date": row["flight_date"],
                "selected_flight_number": "" if not chosen else chosen["selected_flight_number"],
                "selected_price": "" if not chosen else chosen["selected_price"],
                "selected_departure": "" if not chosen else chosen["selected_departure"],
                "selected_arrival": "" if not chosen else chosen["selected_arrival"],
                "tool_called": "search_flights",
            }
        )
PY
