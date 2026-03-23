import json
from pathlib import Path

import pandas as pd


OUTPUT = Path("/root/transfer2_market_report.md")
REQUEST = Path("/root/data/transfer2_market_checks.json")
FLIGHTS = Path("/root/data/flights/clean_Flights_2022.csv")


def build_row(market, flights: pd.DataFrame):
    subset = flights[
        (flights["OriginCityName"] == market["origin"])
        & (flights["DestCityName"] == market["destination"])
        & (flights["FlightDate"] == market["flight_date"])
    ]
    route = f"{market['origin']} -> {market['destination']}"
    if subset.empty:
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

    ordered = subset.sort_values(["Price", "DepTime", "Flight Number"]).reset_index(drop=True)
    cheapest = ordered.iloc[0]
    return {
        "market_id": market["market_id"],
        "route": route,
        "date": market["flight_date"],
        "status": "AVAILABLE",
        "flight_count": str(len(subset)),
        "min_price": str(int(subset["Price"].min())),
        "max_price": str(int(subset["Price"].max())),
        "price_spread": str(int(subset["Price"].max() - subset["Price"].min())),
        "cheapest_flight": cheapest["Flight Number"],
        "cheapest_departure": cheapest["DepTime"],
    }


def expected_report():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    flights = pd.read_csv(FLIGHTS).rename(columns={"Unnamed: 0": "Flight Number"})
    rows = [build_row(market, flights) for market in request["markets"]]
    available = [row for row in rows if row["status"] == "AVAILABLE"]
    available.sort(key=lambda row: (-int(row["price_spread"]), row["market_id"]))
    widest = available[0]
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
    return "\n".join(lines) + "\n"


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer2 output"


def test_report_exact_match():
    assert OUTPUT.read_text(encoding="utf-8") == expected_report()


def test_known_summary_lines():
    report = OUTPUT.read_text(encoding="utf-8")
    assert "- Widest spread market: M1 (172)" in report
    assert "- No-service markets: M6" in report
    assert "| M2 | Boston -> New York | 2022-04-05 | AVAILABLE | 10 | 47 | 88 | 41 | F0264647 | 05:50 |" in report
