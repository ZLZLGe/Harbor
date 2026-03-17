#!/usr/bin/env python3

import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

TASK_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_SKILL_DIR = Path("/root/.codex/skills/civ6lib/scripts")
LOCAL_SKILL_DIR = TASK_ROOT / "environment" / "skills" / "civ6lib" / "scripts"


def _safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except PermissionError:
        return False


if _safe_exists(CONTAINER_SKILL_DIR):
    sys.path.insert(0, str(CONTAINER_SKILL_DIR))
elif _safe_exists(LOCAL_SKILL_DIR):
    sys.path.insert(0, str(LOCAL_SKILL_DIR))
else:
    raise RuntimeError("Unable to locate civ6lib skill scripts")

from adjacency_rules import get_adjacency_calculator
from placement_rules import (
    DistrictType,
    Tile,
    get_placement_rules,
    validate_district_count,
    validate_district_uniqueness,
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def build_tiles_dict(tile_entries: Sequence[Dict[str, Any]]) -> Dict[Tuple[int, int], Tile]:
    tiles: Dict[Tuple[int, int], Tile] = {}
    for tile_data in tile_entries:
        tile = Tile(
            x=tile_data["x"],
            y=tile_data["y"],
            terrain=tile_data.get("terrain", "GRASS"),
            feature=tile_data.get("feature"),
            is_hills=tile_data.get("is_hills", False),
            is_floodplains=tile_data.get("is_floodplains", False),
            river_edges=list(tile_data.get("river_edges", [])),
            river_names=list(tile_data.get("river_names", [])),
            resource=tile_data.get("resource"),
            resource_type=tile_data.get("resource_type"),
            improvement=tile_data.get("improvement"),
        )
        tiles[(tile.x, tile.y)] = tile
    return tiles


def clone_tiles(tiles: Dict[Tuple[int, int], Tile]) -> Dict[Tuple[int, int], Tile]:
    return {
        coord: Tile(
            x=tile.x,
            y=tile.y,
            terrain=tile.terrain,
            feature=tile.feature,
            is_hills=tile.is_hills,
            is_floodplains=tile.is_floodplains,
            river_edges=list(tile.river_edges),
            river_names=list(tile.river_names),
            resource=tile.resource,
            resource_type=tile.resource_type,
            improvement=tile.improvement,
        )
        for coord, tile in tiles.items()
    }


def apply_patch_ids(
    payload: Dict[str, Any],
    selected_ids: Iterable[str],
) -> Dict[Tuple[int, int], Tile]:
    tiles = clone_tiles(build_tiles_dict(payload["tiles"]))
    selected = set(selected_ids)
    for option in payload["patch_options"]:
        if option["patch_id"] not in selected:
            continue
        coord = tuple(option["tile"])
        tile = tiles[coord]
        values = {
            "x": tile.x,
            "y": tile.y,
            "terrain": tile.terrain,
            "feature": tile.feature,
            "is_hills": tile.is_hills,
            "is_floodplains": tile.is_floodplains,
            "river_edges": list(tile.river_edges),
            "river_names": list(tile.river_names),
            "resource": tile.resource,
            "resource_type": tile.resource_type,
            "improvement": tile.improvement,
        }
        values.update(option["changes"])
        tiles[coord] = Tile(**values)
    return tiles


def evaluate_blueprint(
    payload: Dict[str, Any],
    selected_ids: Iterable[str],
) -> Tuple[bool, List[str], int, Dict[str, int]]:
    tiles = apply_patch_ids(payload, selected_ids)
    city_center = tuple(payload["city_center"])
    placements = payload["placements"]
    population = payload["population"]
    errors: List[str] = []

    city_tile = tiles.get(city_center)
    if city_tile is None:
        errors.append(f"City Center: No tile data at {city_center}")
    else:
        if city_tile.is_water:
            errors.append("City Center: Cannot settle on water")
        if city_tile.is_mountain:
            errors.append("City Center: Cannot settle on mountain")
        if city_tile.is_natural_wonder:
            errors.append("City Center: Cannot settle on natural wonder")

    valid_count, count_errors = validate_district_count(placements, population)
    if not valid_count:
        errors.extend(count_errors)

    valid_unique, unique_errors = validate_district_uniqueness(
        placements,
        city_id=payload["scenario_id"],
    )
    if not valid_unique:
        errors.extend(unique_errors)

    if errors:
        return False, errors, 0, {}

    rules = get_placement_rules(tiles, city_center, population)
    existing = {city_center: DistrictType.CITY_CENTER}
    for district_name, coords in placements.items():
        x, y = coords
        result = rules.validate_placement(DistrictType[district_name], x, y, existing)
        if not result.valid:
            errors.extend([f"{district_name}@({x},{y}): {message}" for message in result.errors])
        existing[(x, y)] = DistrictType[district_name]

    if errors:
        return False, errors, 0, {}

    placement_map = {
        tuple(coords): DistrictType[district_name]
        for district_name, coords in placements.items()
    }
    placement_map[city_center] = DistrictType.CITY_CENTER

    total, per_district = get_adjacency_calculator(tiles).calculate_total_adjacency(placement_map)
    bonuses = {
        key.split("@")[0]: result.total_bonus
        for key, result in per_district.items()
    }
    return True, [], total, bonuses


def build_expected_solution(payload: Dict[str, Any]) -> Dict[str, Any]:
    patch_order = [option["patch_id"] for option in payload["patch_options"]]
    patch_index = {patch_id: index for index, patch_id in enumerate(patch_order)}
    option_map = {option["patch_id"]: option for option in payload["patch_options"]}

    for size in range(len(patch_order) + 1):
        for combo in combinations(patch_order, size):
            selected_ids = set(combo)
            legal, _errors, total, bonuses = evaluate_blueprint(payload, selected_ids)
            if not legal:
                continue
            if bonuses != payload["target_adjacency_bonuses"]:
                continue
            if total != payload["target_total_adjacency"]:
                continue

            ordered_ids = sorted(selected_ids, key=patch_index.__getitem__)
            return {
                "scenario_id": payload["scenario_id"],
                "selected_patch_ids": ordered_ids,
                "patch_count": len(ordered_ids),
                "patched_tiles": [
                    {
                        "tile": option_map[patch_id]["tile"],
                        "changes": option_map[patch_id]["changes"],
                    }
                    for patch_id in ordered_ids
                ],
                "blueprint_legal": True,
                "calibrated_adjacency_bonuses": bonuses,
                "calibrated_total_adjacency": total,
            }

    raise AssertionError("Expected at least one valid patch set for this puzzle")
