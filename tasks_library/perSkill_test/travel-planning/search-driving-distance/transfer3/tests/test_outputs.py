import csv
import json
import re
from pathlib import Path


OUTPUT = Path("/root/transfer3_lane_balance_report.json")
REQUEST = Path("/root/data/transfer3_roundtrip_lanes.json")
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


def expected_payload():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    table = load_distances()
    lane_rankings = []
    for lane in request["lanes"]:
        outbound = table[(lane["city_a"], lane["city_b"])]
        returned = table[(lane["city_b"], lane["city_a"])]
        outbound_duration = parse_minutes(outbound["duration"])
        return_duration = parse_minutes(returned["duration"])
        outbound_distance = parse_distance(outbound["distance"])
        return_distance = parse_distance(returned["distance"])
        lane_rankings.append(
            {
                "lane_id": lane["lane_id"],
                "city_a": lane["city_a"],
                "city_b": lane["city_b"],
                "outbound_duration_minutes": outbound_duration,
                "return_duration_minutes": return_duration,
                "duration_delta_minutes": abs(outbound_duration - return_duration),
                "outbound_distance_km": outbound_distance,
                "return_distance_km": return_distance,
                "distance_delta_km": round(abs(outbound_distance - return_distance), 1),
            }
        )

    lane_rankings.sort(
        key=lambda item: (
            item["duration_delta_minutes"],
            item["distance_delta_km"],
            item["lane_id"],
        )
    )

    return {
        "most_balanced_lane_id": lane_rankings[0]["lane_id"],
        "lane_rankings": lane_rankings,
        "tool_called": ["search_driving_distance"],
    }


def test_output_exists():
    assert OUTPUT.exists(), "missing lane balance report"


def test_payload_matches_expected():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload == expected_payload()
