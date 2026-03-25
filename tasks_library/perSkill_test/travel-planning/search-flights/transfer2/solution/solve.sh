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


def build_row(market, result):
    route = f"{market['origin']} -> {market['destination']}"
    if isinstance(result, str):
        return {
            "market_id": market["market_id"],
            "route": route,
            "date": market["flight_date"],
            "status": "NO_SERVICE",
            "flight_count": "-",
            "min_price": "-",
            "max_price": "-",
            "price_spread": "-",
            "cheapest_flight": "-",
            "cheapest_departure": "-",
        }

    ordered = result.sort_values(["Price", "DepTime", "Flight Number"]).reset_index(drop=True)
    cheapest = ordered.iloc[0]
    return {
        "market_id": market["market_id"],
        "route": route,
        "date": market["flight_date"],
        "status": "AVAILABLE",
        "flight_count": str(len(result)),
        "min_price": str(int(result["Price"].min())),
        "max_price": str(int(result["Price"].max())),
        "price_spread": str(int(result["Price"].max() - result["Price"].min())),
        "cheapest_flight": cheapest["Flight Number"],
        "cheapest_departure": cheapest["DepTime"],
    }


request = json.loads(Path("/root/data/transfer2_market_checks.json").read_text(encoding="utf-8"))
search = load_flight_search()
rows = []
for market in request["markets"]:
    result = search(market["origin"], market["destination"], market["flight_date"])
    rows.append(build_row(market, result))

available_rows = [row for row in rows if row["status"] == "AVAILABLE"]
available_rows.sort(
    key=lambda row: (
        -int(row["price_spread"]),
        row["market_id"],
    )
)
widest = available_rows[0]
no_service = [row["market_id"] for row in rows if row["status"] == "NO_SERVICE"]

lines = [
    "# Transfer 2 Market Report",
    "",
    "| market_id | route | date | status | flight_count | min_price | max_price | price_spread | cheapest_flight | cheapest_departure |",
    "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
]

for row in rows:
    lines.append(
        "| {market_id} | {route} | {date} | {status} | {flight_count} | {min_price} | {max_price} | {price_spread} | {cheapest_flight} | {cheapest_departure} |".format(
            **row
        )
    )

lines.extend(
    [
        "",
        "## Summary",
        f"- Widest spread market: {widest['market_id']} ({widest['price_spread']})",
        f"- No-service markets: {', '.join(no_service) if no_service else 'none'}",
        "- Tool called: search_flights",
    ]
)

Path("/root/transfer2_market_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
