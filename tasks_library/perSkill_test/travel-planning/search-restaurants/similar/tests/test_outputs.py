import csv
import json
from pathlib import Path


OUTPUT = Path("/root/similar_dining_route.json")
REQUEST = Path("/root/data/similar_trip_request.json")
DATA = Path("/root/data/restaurants/clean_restaurant_2022.csv")


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_stops():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    rows = load_rows()
    winners = []
    for stop in request["stops"]:
        matches = [
            row
            for row in rows
            if row["City"].strip() == stop["city"]
            and stop["requested_cuisine"].lower() in row["Cuisines"].lower()
            and float(row["Average Cost"]) <= float(stop["max_average_cost"])
            and float(row["Aggregate Rating"]) >= float(stop["min_aggregate_rating"])
        ]
        matches.sort(key=lambda row: (float(row["Average Cost"]), -float(row["Aggregate Rating"]), row["Name"]))
        chosen = matches[0]
        winners.append(
            {
                "slot": stop["slot"],
                "city": stop["city"],
                "requested_cuisine": stop["requested_cuisine"],
                "restaurant_name": chosen["Name"],
                "average_cost": float(chosen["Average Cost"]),
                "aggregate_rating": float(chosen["Aggregate Rating"]),
            }
        )
    return request, winners


def test_output_exists():
    assert OUTPUT.exists(), "missing dining route output"


def test_payload_matches_expected_route():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    request, winners = expected_stops()

    assert payload["trip_name"] == request["trip_name"]
    assert payload["tool_called"] == ["search_restaurants"]
    assert payload["stops"] == winners
    assert payload["total_average_cost"] == sum(item["average_cost"] for item in winners)


def test_known_restaurants_are_selected():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    chosen = {item["slot"]: item["restaurant_name"] for item in payload["stops"]}
    assert chosen == {
        "day1_dinner": "Karnataka Food Centre",
        "day2_lunch": "Makhan Fish and Chicken Corner",
        "day3_dinner": "Bubba Jax Crab Shack",
        "day4_brunch": "Star Noodle",
    }
