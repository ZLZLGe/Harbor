import csv
import re
from pathlib import Path


OUTPUT = Path("/root/transfer1_taxi_quote_sheet.csv")
REQUEST = Path("/root/data/transfer1_courier_requests.csv")
DISTANCE_DATA = Path("/root/data/googleDistanceMatrix/distance.csv")


def parse_minutes(duration_text: str) -> int:
    total = 0
    hour_match = re.search(r"(\d+)\s*hour", duration_text)
    minute_match = re.search(r"(\d+)\s*min", duration_text)
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if minute_match:
        total += int(minute_match.group(1))
    return total


def parse_distance(distance_text: str) -> float:
    return round(float(distance_text.lower().replace("km", "").replace(",", "").strip()), 1)


def load_distances():
    table = {}
    with DISTANCE_DATA.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[(row["origin"].strip(), row["destination"].strip())] = row
    return table


def build_expected_rows():
    table = load_distances()
    rows = []
    with REQUEST.open(encoding="utf-8") as handle:
        for request in csv.DictReader(handle):
            record = table[(request["origin"], request["destination"])]
            distance_km = parse_distance(record["distance"])
            taxi_quote = int(distance_km)
            rows.append(
                {
                    "request_id": request["request_id"],
                    "origin": request["origin"],
                    "destination": request["destination"],
                    "duration_minutes": str(parse_minutes(record["duration"])),
                    "distance_km": f"{distance_km:.1f}",
                    "taxi_quote": str(taxi_quote),
                    "within_budget": "yes" if taxi_quote <= int(request["max_taxi_budget"]) else "no",
                }
            )
    rows.sort(key=lambda item: (int(item["taxi_quote"]), item["request_id"]))
    for index, row in enumerate(rows, start=1):
        row["rank_by_quote"] = str(index)
    return rows


def test_output_exists():
    assert OUTPUT.exists(), "missing taxi quote sheet"


def test_quote_sheet_matches_expected():
    with OUTPUT.open(encoding="utf-8") as handle:
        actual_rows = list(csv.DictReader(handle))

    expected_rows = build_expected_rows()
    assert actual_rows == expected_rows
