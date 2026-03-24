#!/usr/bin/env python3

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, "/tests/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import Tile, DistrictType, get_placement_rules, validate_city_distances, validate_district_count


SCENARIO_PATH = Path("/data/frontier_blueprint_board/scenario.json")
OUTPUT_PATH = Path("/output/blueprint_audit.json")
SCORE_PATH = Path("/logs/verifier/scores/score.txt")


def write_score(value: float) -> None:
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(f"{value:.3f}")


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def build_tiles(tile_rows):
    tiles = {}
    for row in tile_rows:
        tile = Tile(
            x=row["x"],
            y=row["y"],
            terrain=row.get("terrain", "GRASS"),
            feature=row.get("feature"),
            is_hills=row.get("is_hills", False),
            is_floodplains=row.get("is_floodplains", False),
            river_edges=row.get("river_edges", []),
            river_names=row.get("river_names", []),
            resource=row.get("resource"),
            resource_type=row.get("resource_type"),
            improvement=row.get("improvement"),
        )
        tiles[(tile.x, tile.y)] = tile
    return tiles


def invalid_audit(blueprint_id, claimed_total, errors):
    return {
        "blueprint_id": blueprint_id,
        "claimed_total_adjacency": claimed_total,
        "is_valid": False,
        "errors": errors,
        "claim_matches": False,
        "district_adjacency": {},
        "total_adjacency": 0,
    }


def evaluate_blueprint(blueprint, scenario, tiles):
    role_by_id = {role["city_id"]: role for role in scenario["city_roles"]}
    errors = []
    seen_city_ids = []
    normalized_cities = []

    cities = blueprint.get("cities", [])
    if len(cities) != len(role_by_id):
        errors.append(f"expected {len(role_by_id)} cities, got {len(cities)}")

    for city in cities:
        city_id = city.get("city_id")
        if city_id not in role_by_id:
            errors.append(f"unknown city_id: {city_id}")
            continue
        if city_id in seen_city_ids:
            errors.append(f"duplicate city_id: {city_id}")
            continue
        seen_city_ids.append(city_id)

        center = city.get("center")
        if not (isinstance(center, list) and len(center) == 2 and all(isinstance(v, int) for v in center)):
            errors.append(f"{city_id}: invalid center coordinates")
            continue

        district_entries = city.get("districts")
        if not isinstance(district_entries, list):
            errors.append(f"{city_id}: districts must be a list")
            continue

        parsed_entries = []
        for entry in district_entries:
            if not isinstance(entry, dict):
                errors.append(f"{city_id}: each district entry must be an object")
                continue

            district_name = entry.get("district")
            tile = entry.get("tile")
            if not isinstance(district_name, str):
                errors.append(f"{city_id}: district entry missing district name")
                continue
            if not (isinstance(tile, list) and len(tile) == 2 and all(isinstance(v, int) for v in tile)):
                errors.append(f"{city_id}:{district_name}: invalid tile coordinates")
                continue

            parsed_entries.append((district_name, tuple(tile)))

        expected = Counter(role_by_id[city_id]["required_districts"])
        actual = Counter(name for name, _ in parsed_entries)
        if actual != expected:
            errors.append(f"{city_id}: districts must exactly match required_districts")

        duplicates = sorted(name for name, count in actual.items() if count > 1)
        if duplicates:
            errors.append(f"{city_id}: duplicate districts not allowed ({', '.join(duplicates)})")

        normalized_cities.append(
            {
                "city_id": city_id,
                "center": tuple(center),
                "districts": parsed_entries,
            }
        )

    missing_city_ids = [city_id for city_id in role_by_id if city_id not in seen_city_ids]
    if missing_city_ids:
        errors.append("missing city_id entries: " + ", ".join(missing_city_ids))

    if errors:
        return invalid_audit(blueprint["blueprint_id"], blueprint["claimed_total_adjacency"], errors)

    centers = [city["center"] for city in normalized_cities]
    valid_distance, distance_errors = validate_city_distances(centers, tiles)
    if not valid_distance:
        return invalid_audit(blueprint["blueprint_id"], blueprint["claimed_total_adjacency"], distance_errors)

    placements = {city["center"]: DistrictType.CITY_CENTER for city in normalized_cities}
    owner_by_position = {}

    for city in sorted(normalized_cities, key=lambda item: item["city_id"]):
        role = role_by_id[city["city_id"]]
        district_map = {name: list(coord) for name, coord in city["districts"]}
        valid_count, count_errors = validate_district_count(district_map, role["population"])
        if not valid_count:
            return invalid_audit(blueprint["blueprint_id"], blueprint["claimed_total_adjacency"], count_errors)

        rules = get_placement_rules(tiles, city["center"], role["population"])
        for district_name, coord in city["districts"]:
            district_type = getattr(DistrictType, district_name)
            result = rules.validate_placement(district_type, coord[0], coord[1], placements)
            if not result.valid:
                message = f"{city['city_id']}:{district_name} invalid: {'; '.join(result.errors)}"
                return invalid_audit(blueprint["blueprint_id"], blueprint["claimed_total_adjacency"], [message])

            placements[coord] = district_type
            owner_by_position[(coord, district_name)] = f"{city['city_id']}:{district_name}"

    calculator = get_adjacency_calculator(tiles)
    total, per_district = calculator.calculate_total_adjacency(placements)
    district_adjacency = {}

    for key, result in per_district.items():
        district_name, raw_coord = key.split("@", 1)
        coord = tuple(int(part.strip()) for part in raw_coord.strip("()").split(","))
        owner_key = owner_by_position[(coord, district_name)]
        district_adjacency[owner_key] = result.total_bonus

    return {
        "blueprint_id": blueprint["blueprint_id"],
        "claimed_total_adjacency": blueprint["claimed_total_adjacency"],
        "is_valid": True,
        "errors": [],
        "claim_matches": blueprint["claimed_total_adjacency"] == total,
        "district_adjacency": dict(sorted(district_adjacency.items())),
        "total_adjacency": total,
    }


def build_expected_report(scenario):
    tiles = build_tiles(scenario["tiles"])
    audits = [evaluate_blueprint(blueprint, scenario, tiles) for blueprint in scenario["candidate_blueprints"]]
    valid_audits = [audit for audit in audits if audit["is_valid"]]
    valid_audits.sort(key=lambda item: (-item["total_adjacency"], item["blueprint_id"]))
    ranking = [
        {
            "rank": index + 1,
            "blueprint_id": audit["blueprint_id"],
            "total_adjacency": audit["total_adjacency"],
        }
        for index, audit in enumerate(valid_audits)
    ]

    return {
        "scenario_id": scenario["scenario_id"],
        "audits": audits,
        "valid_ranking": ranking,
        "best_valid_blueprint_id": ranking[0]["blueprint_id"],
        "best_valid_total_adjacency": ranking[0]["total_adjacency"],
    }


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_blueprint_audit_report_matches_expected():
    scenario = load_json(SCENARIO_PATH)
    actual = load_json(OUTPUT_PATH)
    expected = build_expected_report(scenario)

    assert actual == expected, f"Audit report mismatch.\nExpected: {expected}\nActual: {actual}"
    write_score(1.0)
