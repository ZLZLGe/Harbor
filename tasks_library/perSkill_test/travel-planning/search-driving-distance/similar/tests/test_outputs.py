import csv
import json
import re
from pathlib import Path


OUTPUT = Path("/root/similar_route_recommendation.json")
REQUEST = Path("/root/data/similar_route_candidates.json")
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


def build_expected():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    table = load_distances()
    route_summaries = []
    route_leg_details = {}
    for candidate in request["route_candidates"]:
        ordered_stops = list(candidate["cities"])
        full_route = [request["start_city"], *ordered_stops, request["start_city"]]
        legs = []
        for index, (origin, destination) in enumerate(zip(full_route, full_route[1:]), start=1):
            record = table[(origin, destination)]
            distance_km = parse_distance(record["distance"])
            legs.append(
                {
                    "leg_number": index,
                    "origin": origin,
                    "destination": destination,
                    "duration_minutes": parse_minutes(record["duration"]),
                    "distance_km": distance_km,
                    "estimated_cost": int(distance_km * 0.05),
                }
            )
        summary = {
            "route_id": candidate["route_id"],
            "ordered_stops": ordered_stops,
            "total_duration_minutes": sum(leg["duration_minutes"] for leg in legs),
            "total_distance_km": round(sum(leg["distance_km"] for leg in legs), 1),
            "total_estimated_cost": sum(leg["estimated_cost"] for leg in legs),
            "leg_count": len(legs),
        }
        route_summaries.append(summary)
        route_leg_details[candidate["route_id"]] = legs

    best = min(route_summaries, key=lambda item: (item["total_duration_minutes"], item["total_distance_km"], item["route_id"]))
    route_summaries.sort(key=lambda item: item["route_id"])
    return request, route_summaries, route_leg_details, best


def test_output_exists():
    assert OUTPUT.exists(), "missing route recommendation output"


def test_recommendation_payload():
    request, route_summaries, route_leg_details, best = build_expected()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))

    assert payload["start_city"] == request["start_city"]
    assert payload["tool_called"] == ["search_driving_distance"]
    assert payload["route_summaries"] == route_summaries
    assert payload["recommended_route_id"] == best["route_id"]
    assert payload["recommended_route_stops"] == best["ordered_stops"]
    assert payload["recommended_legs"] == route_leg_details[best["route_id"]]
