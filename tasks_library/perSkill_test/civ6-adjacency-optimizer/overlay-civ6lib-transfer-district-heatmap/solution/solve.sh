#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, "/solution/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import DistrictType, Tile, get_placement_rules


SCENARIO_PATH = Path("/data/volcanic_hinterland_heatmap/scenario.json")
OUTPUT_PATH = Path("/output/district_heatmap.json")


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


def get_heatmap_entry(district_name, placements, reserved, tiles, center, population, calculator, baseline_total):
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

    return {
        "district": district_name,
        "best_tile": ranked_tiles[0]["tile"],
        "best_district_adjacency": ranked_tiles[0]["district_adjacency"],
        "legal_tile_count": len(ranked_tiles),
        "ranked_tiles": ranked_tiles,
    }


scenario = load_json(SCENARIO_PATH)
tiles = build_tiles(scenario["tiles"])
center = tuple(scenario["city"]["center"])
population = scenario["city"]["population"]
reserved = {tuple(coords) for coords in scenario["reserved_tiles"]}

placements = {center: DistrictType.CITY_CENTER}
for district_name, coords in scenario["locked_districts"].items():
    placements[tuple(coords)] = getattr(DistrictType, district_name)

calculator = get_adjacency_calculator(tiles)
baseline_total, _ = calculator.calculate_total_adjacency(placements)

report = {
    "scenario_id": scenario["scenario_id"],
    "city_center": list(center),
    "baseline_total_adjacency": baseline_total,
    "heatmaps": [],
}

for district_name in scenario["candidate_districts"]:
    report["heatmaps"].append(
        get_heatmap_entry(district_name, placements, reserved, tiles, center, population, calculator, baseline_total)
    )

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(report, f, indent=2)

print(json.dumps({"written_to": str(OUTPUT_PATH), "districts": scenario["candidate_districts"]}, indent=2))
PY
