#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/tests/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import DistrictType, Tile, get_placement_rules


SCENARIO_PATH = Path("/data/volcanic_hinterland_heatmap/scenario.json")
OUTPUT_PATH = Path("/output/district_heatmap.json")
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


def build_base_state(scenario):
    tiles = build_tiles(scenario["tiles"])
    center = tuple(scenario["city"]["center"])
    placements = {center: DistrictType.CITY_CENTER}
    for district_name, coords in scenario["locked_districts"].items():
        placements[tuple(coords)] = getattr(DistrictType, district_name)
    reserved = {tuple(coords) for coords in scenario["reserved_tiles"]}
    calculator = get_adjacency_calculator(tiles)
    baseline_total, _ = calculator.calculate_total_adjacency(placements)
    return tiles, center, placements, reserved, calculator, baseline_total


def enumerate_heatmap_entries(scenario):
    tiles, center, placements, reserved, calculator, baseline_total = build_base_state(scenario)
    population = scenario["city"]["population"]
    expected = []

    for district_name in scenario["candidate_districts"]:
        district_type = getattr(DistrictType, district_name)
        rules = get_placement_rules(tiles, center, population)
        ranked_tiles = []

        for coord in sorted(tiles):
            if coord in placements or coord in reserved:
                continue

            result = rules.validate_placement(district_type, coord[0], coord[1], placements)
            if not result.valid:
                continue

            trial = dict(placements)
            trial[coord] = district_type
            total, per_district = calculator.calculate_total_adjacency(trial)
            placement_key = f"{district_name}@({coord[0]},{coord[1]})"

            ranked_tiles.append(
                {
                    "tile": [coord[0], coord[1]],
                    "district_adjacency": per_district[placement_key].total_bonus,
                    "empire_delta": total - baseline_total,
                    "resulting_total_adjacency": total,
                }
            )

        ranked_tiles.sort(
            key=lambda item: (
                -item["district_adjacency"],
                -item["empire_delta"],
                item["tile"][1],
                item["tile"][0],
            )
        )

        expected.append(
            {
                "district": district_name,
                "best_tile": ranked_tiles[0]["tile"],
                "best_district_adjacency": ranked_tiles[0]["district_adjacency"],
                "legal_tile_count": len(ranked_tiles),
                "ranked_tiles": ranked_tiles,
            }
        )

    return baseline_total, expected


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_heatmap_report_is_exact_and_consistent():
    scenario = load_json(SCENARIO_PATH)
    actual = load_json(OUTPUT_PATH)
    baseline_total, expected_heatmaps = enumerate_heatmap_entries(scenario)

    assert isinstance(actual, dict), "Output must be a JSON object"
    assert actual.get("scenario_id") == scenario["scenario_id"], "scenario_id mismatch"
    assert actual.get("city_center") == scenario["city"]["center"], "city_center mismatch"
    assert actual.get("baseline_total_adjacency") == baseline_total, "baseline_total_adjacency mismatch"
    assert isinstance(actual.get("heatmaps"), list), "heatmaps must be a list"
    assert len(actual["heatmaps"]) == len(scenario["candidate_districts"]), "Incorrect number of heatmaps"

    for actual_entry, expected_entry in zip(actual["heatmaps"], expected_heatmaps):
        assert actual_entry["district"] == expected_entry["district"], "District order mismatch"
        assert actual_entry["legal_tile_count"] == len(actual_entry["ranked_tiles"]), \
            "legal_tile_count must equal the number of ranked tiles"
        assert actual_entry["best_tile"] == actual_entry["ranked_tiles"][0]["tile"], \
            "best_tile must match the first ranked tile"
        assert actual_entry["best_district_adjacency"] == actual_entry["ranked_tiles"][0]["district_adjacency"], \
            "best_district_adjacency must match the first ranked tile"

    assert actual["heatmaps"] == expected_heatmaps, \
        f"Heatmap entries mismatch.\nExpected: {expected_heatmaps}\nActual: {actual['heatmaps']}"
    write_score(1.0)
