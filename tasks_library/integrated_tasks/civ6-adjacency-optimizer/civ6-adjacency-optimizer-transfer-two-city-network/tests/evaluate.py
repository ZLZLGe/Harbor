"""Evaluation helpers for the two-city district-network transfer task."""

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adjacency_rules import get_adjacency_calculator
from placement_rules import (
    DISTRICT_NAME_MAP,
    DistrictType,
    Tile,
    get_placement_rules,
    validate_city_distances,
    validate_district_count,
    validate_district_uniqueness,
)


@dataclass
class EvaluationResult:
    valid: bool
    total_adjacency: int
    optimal_adjacency: int
    score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    per_district: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    adjacency_mismatch: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_tiles_dict(
    scenario: Dict[str, Any],
    data_dir: Optional[Path] = None,
) -> Dict[Tuple[int, int], Tile]:
    """Load tiles either from scenario['tiles'] or the referenced .Civ6Map."""
    if "map_file" in scenario and data_dir:
        map_path = data_dir / scenario["map_file"]
        if map_path.exists():
            tools_dir = Path(__file__).parent / "tools"
            if str(tools_dir) not in sys.path:
                sys.path.insert(0, str(tools_dir))
            from civ6map_to_scenario import convert_civ6map

            parsed = convert_civ6map(str(map_path))
            scenario = {**scenario, "tiles": parsed["tiles"]}

    tiles: Dict[Tuple[int, int], Tile] = {}
    for tile_data in scenario.get("tiles", []):
        tile = Tile(
            x=tile_data["x"],
            y=tile_data["y"],
            terrain=tile_data.get("terrain", "GRASS"),
            feature=tile_data.get("feature"),
            is_hills=tile_data.get("is_hills", False),
            is_floodplains=tile_data.get("is_floodplains", False),
            river_edges=tile_data.get("river_edges", []),
            river_names=tile_data.get("river_names", []),
            resource=tile_data.get("resource"),
            resource_type=tile_data.get("resource_type"),
            improvement=tile_data.get("improvement"),
        )
        tiles[(tile.x, tile.y)] = tile
    return tiles


def evaluate_solution(
    scenario: Dict[str, Any],
    solution: Dict[str, Any],
    ground_truth: Dict[str, Any],
    data_dir: Optional[Path] = None,
) -> EvaluationResult:
    result = EvaluationResult(
        valid=False,
        total_adjacency=0,
        optimal_adjacency=ground_truth.get("optimal_adjacency", 0),
        score=0.0,
    )

    tiles = build_tiles_dict(scenario, data_dir)
    city_slots = scenario.get("city_slots", [])
    expected_city_ids = [slot["id"] for slot in city_slots]
    district_pool = scenario.get("district_pool", [])

    cities_output = solution.get("cities")
    if not isinstance(cities_output, dict):
        result.errors.append("Solution must include a 'cities' object")
        return result

    if set(cities_output.keys()) != set(expected_city_ids):
        result.errors.append(
            f"Expected city ids {expected_city_ids}, got {sorted(cities_output.keys())}"
        )
        return result

    city_centers: List[Tuple[int, int]] = []
    per_city_placements: Dict[str, Dict[str, List[int]]] = {}
    all_district_names: List[str] = []
    all_positions: Dict[Tuple[int, int], str] = {}

    for slot in city_slots:
        city_id = slot["id"]
        city_output = cities_output[city_id]
        center = tuple(city_output.get("center", []))
        candidate_centers = {tuple(center_xy) for center_xy in slot.get("candidate_centers", [])}

        if len(center) != 2:
            result.errors.append(f"{city_id}: center must be a [x, y] pair")
            continue
        if center not in candidate_centers:
            result.errors.append(f"{city_id}: center {center} is not in candidate_centers")
            continue

        tile = tiles.get(center)
        if tile is None:
            result.errors.append(f"{city_id}: no tile data at center {center}")
            continue
        if tile.is_water:
            result.errors.append(f"{city_id}: cannot settle on water at {center}")
        if tile.is_mountain:
            result.errors.append(f"{city_id}: cannot settle on mountain at {center}")
        if tile.is_natural_wonder:
            result.errors.append(f"{city_id}: cannot settle on natural wonder at {center}")

        city_centers.append(center)

        raw_placements = city_output.get("placements", {})
        if not isinstance(raw_placements, dict):
            result.errors.append(f"{city_id}: placements must be a dict")
            continue

        per_city_placements[city_id] = raw_placements
        all_district_names.extend(raw_placements.keys())

    if result.errors:
        return result

    valid_distances, distance_errors = validate_city_distances(city_centers, tiles)
    if not valid_distances:
        result.errors.extend([f"City distance violation: {err}" for err in distance_errors])
        return result

    if sorted(all_district_names) != sorted(district_pool):
        result.errors.append(
            f"Placed districts must exactly match district_pool: expected {sorted(district_pool)}, got {sorted(all_district_names)}"
        )
        return result

    valid_global_unique = True
    for slot in city_slots:
        city_id = slot["id"]
        population = slot["population"]
        raw_placements = per_city_placements[city_id]

        valid_count, count_errors = validate_district_count(raw_placements, population)
        if not valid_count:
            result.errors.extend([f"{city_id}: {err}" for err in count_errors])
            valid_global_unique = False

        valid_unique, unique_errors = validate_district_uniqueness(
            raw_placements,
            city_id=city_id,
            all_placements=per_city_placements,
        )
        if not valid_unique:
            result.errors.extend(unique_errors)
            valid_global_unique = False

    if not valid_global_unique or result.errors:
        return result

    # Preload city centers into the occupied map.
    occupied: Dict[Tuple[int, int], DistrictType] = {}
    city_center_by_id = {slot["id"]: tuple(cities_output[slot["id"]]["center"]) for slot in city_slots}
    for center in city_center_by_id.values():
        occupied[center] = DistrictType.CITY_CENTER

    district_owner: Dict[str, str] = {}
    for slot in city_slots:
        city_id = slot["id"]
        center = city_center_by_id[city_id]
        population = slot["population"]
        rules = get_placement_rules(tiles, center, population)

        for district_name, coords in per_city_placements[city_id].items():
            if district_name not in DISTRICT_NAME_MAP:
                result.errors.append(f"{city_id}: unknown district type {district_name}")
                continue
            if not isinstance(coords, list) or len(coords) != 2:
                result.errors.append(f"{city_id}: {district_name} must use [x, y] coordinates")
                continue

            coord = (coords[0], coords[1])
            if coord in all_positions:
                result.errors.append(
                    f"Duplicate placement at {coord}: {all_positions[coord]} and {city_id}:{district_name}"
                )
                continue
            if coord in occupied:
                result.errors.append(f"{city_id}: {district_name} overlaps an existing city center at {coord}")
                continue

            validation = rules.validate_placement(
                DISTRICT_NAME_MAP[district_name],
                coord[0],
                coord[1],
                occupied,
            )
            if not validation.valid:
                for err in validation.errors:
                    result.errors.append(f"{city_id}:{district_name}@{coord}: {err}")
                continue

            for warning in validation.warnings:
                result.warnings.append(f"{city_id}:{district_name}@{coord}: {warning}")

            all_positions[coord] = f"{city_id}:{district_name}"
            occupied[coord] = DISTRICT_NAME_MAP[district_name]
            district_owner[district_name] = city_id

    if result.errors:
        return result

    calculator = get_adjacency_calculator(tiles)
    total, per_district = calculator.calculate_total_adjacency(occupied)
    result.total_adjacency = total
    result.valid = True

    calculated_city_bonuses: Dict[str, Dict[str, int]] = {slot["id"]: {} for slot in city_slots}
    calculated_city_totals: Dict[str, int] = {slot["id"]: 0 for slot in city_slots}

    for district_key, adj_result in per_district.items():
        district_name = district_key.split("@")[0]
        owner = district_owner[district_name]
        calculated_city_bonuses[owner][district_name] = adj_result.total_bonus
        calculated_city_totals[owner] += adj_result.total_bonus
        result.per_district[district_key] = {
            "bonus": adj_result.total_bonus,
            "breakdown": adj_result.breakdown,
        }

    for slot in city_slots:
        city_id = slot["id"]
        city_output = cities_output[city_id]
        solver_bonuses = city_output.get("adjacency_bonuses")
        solver_total = city_output.get("total_adjacency")

        if solver_bonuses != calculated_city_bonuses[city_id]:
            result.errors.append(
                f"{city_id}: adjacency_bonuses mismatch. submitted={solver_bonuses}, calculated={calculated_city_bonuses[city_id]}"
            )
        if solver_total != calculated_city_totals[city_id]:
            result.errors.append(
                f"{city_id}: total_adjacency mismatch. submitted={solver_total}, calculated={calculated_city_totals[city_id]}"
            )

    solver_total = solution.get("total_adjacency")
    if solver_total != total:
        result.errors.append(
            f"Global total_adjacency mismatch. submitted={solver_total}, calculated={total}"
        )
        result.adjacency_mismatch = True

    if result.errors:
        result.valid = False
        result.score = 0.0
        return result

    optimal = result.optimal_adjacency
    if optimal > 0:
        result.score = min(1.0, result.total_adjacency / optimal)
    else:
        result.score = 1.0 if result.total_adjacency == 0 else 0.0

    return result


def run_evaluation(
    scenario_path: Path,
    solution_path: Path,
    ground_truth_path: Path,
) -> Dict[str, Any]:
    with open(scenario_path) as f:
        scenario = json.load(f)
    with open(solution_path) as f:
        solution = json.load(f)
    with open(ground_truth_path) as f:
        ground_truth = json.load(f)

    result = evaluate_solution(
        scenario=scenario,
        solution=solution,
        ground_truth=ground_truth,
        data_dir=scenario_path.parent.parent,
    )

    return {
        "scenario_id": scenario.get("id", "unknown"),
        "valid": result.valid,
        "total_adjacency": result.total_adjacency,
        "optimal_adjacency": result.optimal_adjacency,
        "score": result.score,
        "errors": result.errors,
        "warnings": result.warnings,
        "per_district": result.per_district,
        "adjacency_mismatch": result.adjacency_mismatch,
    }
