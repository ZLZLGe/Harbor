import csv
import json
from pathlib import Path


OUTPUT = Path("/root/transfer3_cuisine_matrix.csv")
REQUEST = Path("/root/data/transfer3_matrix_request.json")
DATA = Path("/root/data/restaurants/clean_restaurant_2022.csv")


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_expected_rows():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    rows = load_rows()
    expected = []
    for city in request["cities"]:
        city_rows = [row for row in rows if row["City"].strip() == city]
        for cuisine in request["cuisines"]:
            matches = [row for row in city_rows if cuisine.lower() in row["Cuisines"].lower()]
            cheapest = sorted(
                matches,
                key=lambda row: (float(row["Average Cost"]), -float(row["Aggregate Rating"]), row["Name"]),
            )[0]
            highest = sorted(
                matches,
                key=lambda row: (-float(row["Aggregate Rating"]), float(row["Average Cost"]), row["Name"]),
            )[0]
            expected.append(
                {
                    "city": city,
                    "requested_cuisine": cuisine,
                    "match_count": str(len(matches)),
                    "cheapest_restaurant": cheapest["Name"],
                    "cheapest_cost": str(float(cheapest["Average Cost"])),
                    "highest_rated_restaurant": highest["Name"],
                    "highest_rating": str(float(highest["Aggregate Rating"])),
                }
            )
    return expected


def test_output_exists():
    assert OUTPUT.exists(), "missing cuisine matrix output"


def test_csv_matches_expected_rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        actual = list(csv.DictReader(handle))

    assert actual == build_expected_rows()


def test_known_reference_rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        actual = list(csv.DictReader(handle))

    row_map = {(row["city"], row["requested_cuisine"]): row for row in actual}
    assert row_map[("Akron", "Chinese")] == {
        "city": "Akron",
        "requested_cuisine": "Chinese",
        "match_count": "2",
        "cheapest_restaurant": "Miann",
        "cheapest_cost": "45.0",
        "highest_rated_restaurant": "Miann",
        "highest_rating": "4.9",
    }
    assert row_map[("Minneapolis", "Mediterranean")] == {
        "city": "Minneapolis",
        "requested_cuisine": "Mediterranean",
        "match_count": "8",
        "cheapest_restaurant": "The Cafe",
        "cheapest_cost": "14.0",
        "highest_rated_restaurant": "The Cafe",
        "highest_rating": "4.9",
    }
