import json
import os
from pathlib import Path

import pandas as pd


PLAN_PATH = Path(os.environ.get("PLAN_PATH", "/app/output/city_break_guide.json"))
REQUEST_PATH = Path(os.environ.get("REQUEST_PATH", "/app/data/city_break_request.json"))
ATTRACTIONS_PATH = Path(os.environ.get("ATTRACTIONS_PATH", "/app/data/attractions/attractions.csv"))


def load_request():
    with REQUEST_PATH.open() as f:
        return json.load(f)


def load_plan():
    with PLAN_PATH.open() as f:
        return json.load(f)


def build_city_lookup():
    frame = pd.read_csv(ATTRACTIONS_PATH)
    frame = frame[["Name", "Address", "Website", "City"]].dropna()
    lookup = {}
    for _, row in frame.iterrows():
        city = str(row["City"]).strip().lower()
        entry = (
            str(row["Name"]),
            str(row["Address"]),
            str(row["Website"]),
        )
        lookup.setdefault(city, set()).add(entry)
    return lookup


def expand_expected_days():
    request = load_request()
    expanded = []
    for stop in request["city_stays"]:
        for _ in range(stop["days"]):
            expanded.append(stop)
    return expanded


def test_output_exists():
    assert PLAN_PATH.exists(), f"Missing output file: {PLAN_PATH}"


def test_top_level_structure():
    request = load_request()
    payload = load_plan()

    assert isinstance(payload, dict)
    assert payload.get("trip_name") == request["trip_name"]
    assert isinstance(payload.get("days"), list)


def test_day_count_and_order():
    payload = load_plan()
    expected_days = expand_expected_days()

    assert len(payload["days"]) == len(expected_days)
    for idx, (day, expected) in enumerate(zip(payload["days"], expected_days), start=1):
        assert day["day"] == idx
        assert day["current_city"] == expected["city"]


def test_focus_mentions_city_keyword():
    payload = load_plan()
    expected_days = expand_expected_days()

    for day, expected in zip(payload["days"], expected_days):
        focus = str(day["focus"]).lower()
        assert any(keyword.lower() in focus for keyword in expected["focus_keywords"])


def test_time_blocks_match_requested_sizes():
    payload = load_plan()
    request = load_request()
    selector = request["selection_rules"]

    for day in payload["days"]:
        assert len(day["morning_attractions"]) == selector["morning_count"]
        assert len(day["afternoon_attractions"]) == selector["afternoon_count"]
        assert len(day["evening_attractions"]) == selector["evening_count"]


def test_attraction_entries_are_complete_and_city_matched():
    payload = load_plan()
    city_lookup = build_city_lookup()

    for day in payload["days"]:
        city_key = day["current_city"].lower()
        seen_names = set()
        for block in ["morning_attractions", "afternoon_attractions", "evening_attractions"]:
            for item in day[block]:
                assert set(item.keys()) == {"name", "address", "website"}
                assert all(isinstance(item[key], str) and item[key].strip() for key in item)
                triple = (item["name"], item["address"], item["website"])
                assert triple in city_lookup[city_key]
                assert item["name"] not in seen_names
                seen_names.add(item["name"])
