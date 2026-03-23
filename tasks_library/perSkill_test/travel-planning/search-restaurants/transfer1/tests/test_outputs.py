import csv
import json
from pathlib import Path


OUTPUT = Path("/root/transfer1_host_city_brief.json")
REQUEST = Path("/root/data/transfer1_host_request.json")
DATA = Path("/root/data/restaurants/clean_restaurant_2022.csv")


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_expected():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    rows = load_rows()
    summaries = []
    for city in request["candidate_cities"]:
        city_rows = [row for row in rows if row["City"].strip() == city]
        bundle = []
        missing = []
        for cuisine in request["target_cuisines"]:
            matches = [
                row
                for row in city_rows
                if cuisine.lower() in row["Cuisines"].lower()
                and float(row["Average Cost"]) <= float(request["max_average_cost"])
            ]
            matches.sort(key=lambda row: (float(row["Average Cost"]), -float(row["Aggregate Rating"]), row["Name"]))
            if matches:
                chosen = matches[0]
                bundle.append(
                    {
                        "cuisine": cuisine,
                        "restaurant_name": chosen["Name"],
                        "average_cost": float(chosen["Average Cost"]),
                        "aggregate_rating": float(chosen["Aggregate Rating"]),
                    }
                )
            else:
                missing.append(cuisine)
        summaries.append(
            {
                "city": city,
                "covered_cuisine_count": len(bundle),
                "missing_cuisines": missing,
                "estimated_bundle_cost": sum(item["average_cost"] for item in bundle),
                "bundle": bundle,
            }
        )
    recommended = sorted(
        summaries,
        key=lambda item: (-item["covered_cuisine_count"], item["estimated_bundle_cost"], item["city"]),
    )[0]["city"]
    return request, recommended, summaries


def test_output_exists():
    assert OUTPUT.exists(), "missing host city brief output"


def test_payload_matches_expected_brief():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    request, recommended, summaries = build_expected()

    assert payload["brief_name"] == request["brief_name"]
    assert payload["recommended_city"] == recommended
    assert payload["city_summaries"] == summaries
    assert payload["tool_called"] == ["search_restaurants"]


def test_known_winner_and_gaps():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    summary_map = {item["city"]: item for item in payload["city_summaries"]}

    assert payload["recommended_city"] == "Boise"
    assert summary_map["Dallas"]["missing_cuisines"] == ["Chinese", "Italian"]
    assert summary_map["Boise"]["estimated_bundle_cost"] == 54.0
