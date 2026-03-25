import csv
import json
from pathlib import Path

import pandas as pd


APP_ROOT = Path(__import__("os").environ.get("APP_ROOT", "/app"))

OUTPUT_PATH = APP_ROOT / "output" / "conference_free_time_brief.md"
CITY_PATH = APP_ROOT / "data" / "conference_cities.csv"
SLOT_PATH = APP_ROOT / "data" / "free_time_slots.json"
ATTRACTIONS_PATH = APP_ROOT / "data" / "attractions" / "attractions.csv"


def load_city_rows():
    with CITY_PATH.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_slots():
    with SLOT_PATH.open() as handle:
        return json.load(handle)["slots"]


def load_output():
    return OUTPUT_PATH.read_text()


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


def parse_sections(text):
    sections = {}
    current_city = None
    current_slot = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_city = line[3:].strip()
            sections[current_city] = {}
            current_slot = None
        elif line.startswith("### "):
            if current_city is None:
                raise AssertionError("Slot heading appears before any city heading.")
            current_slot = line[4:].strip()
            sections[current_city][current_slot] = []
        elif line.startswith("- "):
            if current_city is None or current_slot is None:
                raise AssertionError("Bullet appears before city and slot headings.")
            parts = [part.strip() for part in line[2:].split(" | ")]
            assert len(parts) == 3, f"Bullet must have 3 pipe-separated fields: {line}"
            sections[current_city][current_slot].append(tuple(parts))

    return sections


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_title_line():
    first_line = load_output().splitlines()[0]
    assert first_line == "# Conference Free-Time City Brief"


def test_city_order_matches_input():
    text = load_output()
    sections = parse_sections(text)
    expected_cities = [row["city"] for row in load_city_rows()]
    assert list(sections.keys()) == expected_cities


def test_all_slots_present_in_each_city():
    sections = parse_sections(load_output())
    expected_slots = [slot["slot"] for slot in load_slots()]

    for city, city_slots in sections.items():
        assert list(city_slots.keys()) == expected_slots, f"Unexpected slots for {city}"


def test_slot_counts_match_rules():
    sections = parse_sections(load_output())
    expected_counts = {slot["slot"]: slot["count"] for slot in load_slots()}

    for city, city_slots in sections.items():
        for slot_name, expected_count in expected_counts.items():
            assert len(city_slots[slot_name]) == expected_count, (
                f"{city} / {slot_name} should contain {expected_count} attractions"
            )


def test_entries_match_city_dataset_exactly():
    sections = parse_sections(load_output())
    lookup = build_lookup()

    for city, city_slots in sections.items():
        assert city in lookup, f"City not found in attraction data: {city}"
        seen_names = set()
        for entries in city_slots.values():
            for name, address, website in entries:
                assert (name, address, website) in lookup[city]
                assert name not in seen_names, f"Duplicate attraction in {city}: {name}"
                seen_names.add(name)


def test_no_missing_or_blank_fields():
    sections = parse_sections(load_output())

    for city_slots in sections.values():
        for entries in city_slots.values():
            for triple in entries:
                assert all(isinstance(value, str) and value.strip() for value in triple)
