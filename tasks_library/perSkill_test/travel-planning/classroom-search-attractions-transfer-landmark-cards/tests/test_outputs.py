import csv
import json
import os
from pathlib import Path

import pandas as pd


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))

OUTPUT_PATH = APP_ROOT / "output" / "landmark_cards.csv"
CITY_PATH = APP_ROOT / "data" / "classroom_cities.txt"
TEMPLATE_PATH = APP_ROOT / "data" / "card_export_template.json"
ATTRACTIONS_PATH = APP_ROOT / "data" / "attractions" / "attractions.csv"


def load_cities():
    return [line.strip() for line in CITY_PATH.read_text().splitlines() if line.strip()]


def load_template():
    with TEMPLATE_PATH.open() as handle:
        return json.load(handle)


def load_rows():
    with OUTPUT_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def build_lookup():
    frame = pd.read_csv(ATTRACTIONS_PATH)
    frame = frame[["City", "Name", "Address", "Website"]].dropna().drop_duplicates()
    lookup = {}
    for _, row in frame.iterrows():
        city = str(row["City"]).strip()
        triple = (
            str(row["Name"]),
            str(row["Address"]),
            str(row["Website"]),
        )
        lookup.setdefault(city, set()).add(triple)
    return lookup


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_header_matches_template_columns():
    fieldnames, _ = load_rows()
    assert fieldnames == load_template()["columns"]


def test_row_count_matches_city_and_group_requirements():
    _, rows = load_rows()
    cities = load_cities()
    groups = load_template()["card_groups"]
    assert len(rows) == len(cities) * len(groups)


def test_city_and_group_order_match_inputs():
    _, rows = load_rows()
    cities = load_cities()
    groups = [item["card_group"] for item in load_template()["card_groups"]]

    expected_pairs = []
    for city in cities:
        for group in groups:
            expected_pairs.append((city, group))

    actual_pairs = [(row["city"], row["card_group"]) for row in rows]
    assert actual_pairs == expected_pairs


def test_rows_are_non_blank():
    _, rows = load_rows()
    for row in rows:
        assert set(row.keys()) == {"city", "card_group", "attraction_name", "address", "website"}
        assert all(isinstance(value, str) and value.strip() for value in row.values())


def test_attractions_match_exact_city_dataset():
    _, rows = load_rows()
    lookup = build_lookup()

    for row in rows:
        city = row["city"]
        triple = (row["attraction_name"], row["address"], row["website"])
        assert city in lookup, f"City not found in attraction data: {city}"
        assert triple in lookup[city], f"Attraction does not match the dataset for {city}: {triple}"


def test_no_duplicate_attraction_names_within_city():
    _, rows = load_rows()
    seen_by_city = {}

    for row in rows:
        city = row["city"]
        seen_by_city.setdefault(city, set())
        name = row["attraction_name"]
        assert name not in seen_by_city[city], f"Duplicate attraction within {city}: {name}"
        seen_by_city[city].add(name)
