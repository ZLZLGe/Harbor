"""Evaluation helpers for the coastal infrastructure transfer task."""

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
    validate_district_count,
    validate_district_uniqueness,
)


@dataclass
class EvaluationResult:
    valid: bool
    total_adjacency: int
    weighted_score: int
    optimal_weighted_score: int
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
        weighted_score=0,
        optimal_weighted_score=ground_truth.get("optimal_weighted_score", 0),
        score=0.0,
    )

    tiles = build_tiles_dict(scenario, data_dir)
    candidate_centers = {tuple(center) for center in scenario.get("candidate_city_centers", [])}
    district_pool = scenario.get("district_pool", [])
    score_weights = scenario.get("score_weights", {})
    population = scenario.get("population", 7)

    city_center_raw = solution.get("city_center")
    if not isinstance(city_center_raw, list) or len(city_center_raw) != 2:
        result.errors.append("Solution must include 'city_center' as [x, y]")
        return result

    city_center = tuple(city_center_raw)
    if city_center not in candidate_centers:
        result.errors.append(f"city_center {city_center} is not in candidate_city_centers")
        return result

    city_tile = tiles.get(city_center)
    if city_tile is None:
        result.errors.append(f"No tile data at city_center {city_center}")
        return result
    if city_tile.is_water:
        result.errors.append("City center cannot be on water")
    if city_tile.is_mountain:
        result.errors.append("City center cannot be on mountain")
    if city_tile.is_natural_wonder:
        result.errors.append("City center cannot be on natural wonder")
    if result.errors:
        return result

    raw_placements = solution.get("placements")
    if not isinstance(raw_placements, dict):
        result.errors.append("Solution must include a 'placements' object")
        return result

    if set(raw_placements.keys()) != set(district_pool):
        result.errors.append(
            f"placements keys must exactly match district_pool: expected {district_pool}, got {list(raw_placements.keys())}"
        )
        return result

    valid_count, count_errors = validate_district_count(raw_placements, population)
    if not valid_count:
        result.errors.extend(count_errors)
        return result

    valid_unique, unique_errors = validate_district_uniqueness(raw_placements, city_id="coastal_city")
    if not valid_unique:
        result.errors.extend(unique_errors)
        return result

    rules = get_placement_rules(tiles, city_center, population)
    occupied: Dict[Tuple[int, int], DistrictType] = {city_center: DistrictType.CITY_CENTER}

    for district_name in district_pool:
        if district_name not in DISTRICT_NAME_MAP:
            result.errors.append(f"Unknown district type {district_name}")
            continue

        coords = raw_placements.get(district_name)
        if not isinstance(coords, list) or len(coords) != 2:
            result.errors.append(f"{district_name} must use [x, y] coordinates")
            continue

        coord = (coords[0], coords[1])
        if coord in occupied:
            result.errors.append(f"{district_name} overlaps an occupied tile at {coord}")
            continue

        validation = rules.validate_placement(
            DISTRICT_NAME_MAP[district_name],
            coord[0],
            coord[1],
            occupied,
        )
        if not validation.valid:
            for err in validation.errors:
                result.errors.append(f"{district_name}@{coord}: {err}")
            continue

        for warning in validation.warnings:
            result.warnings.append(f"{district_name}@{coord}: {warning}")

        occupied[coord] = DISTRICT_NAME_MAP[district_name]

    if result.errors:
        return result

    calculator = get_adjacency_calculator(tiles)
    total, per_district = calculator.calculate_total_adjacency(occupied)
    result.total_adjacency = total
    result.valid = True

    calculated_bonuses: Dict[str, int] = {}
    calculated_breakdowns: Dict[str, Dict[str, Any]] = {}
    for district_key, adj_result in per_district.items():
        district_name = district_key.split("@")[0]
        calculated_bonuses[district_name] = adj_result.total_bonus
        calculated_breakdowns[district_name] = adj_result.breakdown
        result.per_district[district_key] = {
            "bonus": adj_result.total_bonus,
            "breakdown": adj_result.breakdown,
        }

    weighted_score = 0
    for district_name, weight in score_weights.items():
        weighted_score += calculated_bonuses.get(district_name, 0) * weight
    result.weighted_score = weighted_score

    solver_bonuses = solution.get("adjacency_bonuses")
    if solver_bonuses != calculated_bonuses:
        result.errors.append(
            f"adjacency_bonuses mismatch. submitted={solver_bonuses}, calculated={calculated_bonuses}"
        )

    solver_breakdowns = solution.get("adjacency_breakdowns")
    if solver_breakdowns != calculated_breakdowns:
        result.errors.append(
            f"adjacency_breakdowns mismatch. submitted={solver_breakdowns}, calculated={calculated_breakdowns}"
        )

    solver_total = solution.get("total_adjacency")
    if solver_total != total:
        result.errors.append(
            f"total_adjacency mismatch. submitted={solver_total}, calculated={total}"
        )
        result.adjacency_mismatch = True

    solver_weighted = solution.get("weighted_score")
    if solver_weighted != weighted_score:
        result.errors.append(
            f"weighted_score mismatch. submitted={solver_weighted}, calculated={weighted_score}"
        )

    if result.errors:
        result.valid = False
        result.score = 0.0
        return result

    optimal = result.optimal_weighted_score
    if optimal > 0:
        result.score = min(1.0, result.weighted_score / optimal)
    else:
        result.score = 1.0 if result.weighted_score == 0 else 0.0

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
        "weighted_score": result.weighted_score,
        "optimal_weighted_score": result.optimal_weighted_score,
        "score": result.score,
        "errors": result.errors,
        "warnings": result.warnings,
        "per_district": result.per_district,
        "adjacency_mismatch": result.adjacency_mismatch,
    }
