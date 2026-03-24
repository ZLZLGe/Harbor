#!/usr/bin/env python3

import json
from itertools import combinations
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = Path("/data/warehouse_layout_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/warehouse_layout_scenario.json"

OUTPUT_PATH = Path("/output/warehouse_service_layout.json")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/warehouse_service_layout.json"

SCORE_PATH = Path("/logs/verifier/scores/warehouse_service_layout.txt")
if not SCORE_PATH.parent.exists():
    SCORE_PATH = TASK_ROOT / ".tmp_logs/verifier/scores/warehouse_service_layout.txt"


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def parse_layout(layout):
    fire_aisles = set()
    service_pads = set()
    shelves = set()
    for y, row in enumerate(layout):
        for x, cell in enumerate(row):
            if cell == "F":
                fire_aisles.add((x, y))
            elif cell == "P":
                service_pads.add((x, y))
            elif cell == "S":
                shelves.add((x, y))
    return fire_aisles, service_pads, shelves


def valid_service_pads(scenario):
    fire_aisles, service_pads, _ = parse_layout(scenario["layout"])
    clearance = scenario["fire_clearance_distance"]
    valid = {
        pad
        for pad in service_pads
        if all(manhattan(pad, fire_cell) > clearance for fire_cell in fire_aisles)
    }
    return fire_aisles, service_pads, valid


def score_for_distance(rule, demand, distance):
    return demand * rule["distance_scores"].get(str(distance), 0)


def best_device_entry(device_type, candidates, shelf, scenario):
    rule = scenario["service_rules"][device_type]
    demand = shelf[rule["demand_field"]]

    best_score = 0
    best_coord = None
    best_distance = None
    best_sort_key = None

    for coord in candidates:
        distance = manhattan(tuple(shelf["coord"]), coord)
        score = score_for_distance(rule, demand, distance)
        if score == 0:
            continue
        sort_key = (score, -distance, -coord[1], -coord[0])
        if best_sort_key is None or sort_key > best_sort_key:
            best_sort_key = sort_key
            best_score = score
            best_coord = coord
            best_distance = distance

    return {
        "coord": list(best_coord) if best_coord is not None else None,
        "distance": best_distance,
        "score": best_score,
    }


def evaluate_solution_payload(solution, scenario):
    placements = solution["placements"]
    pick_stations = [tuple(coord) for coord in placements["pick_stations"]]
    charging_dock = tuple(placements["charging_dock"])
    buffer_tables = [tuple(coord) for coord in placements["buffer_tables"]]

    shelf_service = {}
    total_service_score = 0
    for shelf in scenario["shelves"]:
        pick_entry = best_device_entry("pick_station", pick_stations, shelf, scenario)
        charge_entry = best_device_entry("charging_dock", [charging_dock], shelf, scenario)
        buffer_entry = best_device_entry("buffer_table", buffer_tables, shelf, scenario)
        shelf_total = pick_entry["score"] + charge_entry["score"] + buffer_entry["score"]
        shelf_service[shelf["id"]] = {
            "pick_station": pick_entry,
            "charging_dock": charge_entry,
            "buffer_table": buffer_entry,
            "total": shelf_total,
        }
        total_service_score += shelf_total

    return shelf_service, total_service_score


def assert_legal_layout(solution, scenario):
    fire_aisles, service_pads, valid_pads = valid_service_pads(scenario)
    _, _, shelf_cells = parse_layout(scenario["layout"])

    placements = solution["placements"]
    pick_stations = placements["pick_stations"]
    buffer_tables = placements["buffer_tables"]
    charging_dock = placements["charging_dock"]

    all_coords = [tuple(coord) for coord in pick_stations]
    all_coords.append(tuple(charging_dock))
    all_coords.extend(tuple(coord) for coord in buffer_tables)

    assert len(all_coords) == (
        scenario["device_counts"]["pick_station"]
        + scenario["device_counts"]["charging_dock"]
        + scenario["device_counts"]["buffer_table"]
    )
    assert len(set(all_coords)) == len(all_coords), "two devices occupy the same pad"

    for coord in all_coords:
        assert coord in service_pads, f"{coord} is not a marked service pad"
        assert coord not in shelf_cells, f"{coord} overlaps a shelf"
        assert coord in valid_pads, f"{coord} violates fire-aisle clearance"
        assert all(
            manhattan(coord, fire_cell) > scenario["fire_clearance_distance"]
            for fire_cell in fire_aisles
        )

    for index, coord in enumerate(all_coords):
        for other in all_coords[index + 1:]:
            assert (
                manhattan(coord, other) >= scenario["min_device_spacing"]
            ), f"{coord} and {other} are too close"


def find_optimal_total(scenario):
    _, _, valid_pads = valid_service_pads(scenario)
    valid_pads = sorted(valid_pads)
    best_total = -1

    for pick_stations in combinations(valid_pads, scenario["device_counts"]["pick_station"]):
        remaining_after_pick = [pad for pad in valid_pads if pad not in pick_stations]
        for charging_dock in remaining_after_pick:
            remaining_after_charge = [pad for pad in remaining_after_pick if pad != charging_dock]
            for buffer_tables in combinations(remaining_after_charge, scenario["device_counts"]["buffer_table"]):
                coords = list(pick_stations) + [charging_dock] + list(buffer_tables)
                if any(
                    manhattan(a, b) < scenario["min_device_spacing"]
                    for i, a in enumerate(coords)
                    for b in coords[i + 1:]
                ):
                    continue
                solution = {
                    "placements": {
                        "pick_stations": [list(coord) for coord in pick_stations],
                        "charging_dock": list(charging_dock),
                        "buffer_tables": [list(coord) for coord in buffer_tables],
                    }
                }
                _, total = evaluate_solution_payload(solution, scenario)
                if total > best_total:
                    best_total = total

    return best_total


def run_checks():
    assert OUTPUT_PATH.exists(), f"solution file not found: {OUTPUT_PATH}"
    with SCENARIO_PATH.open() as f:
        scenario = json.load(f)
    with OUTPUT_PATH.open() as f:
        solution = json.load(f)

    assert set(solution) == {"placements", "shelf_service", "total_service_score"}

    placements = solution["placements"]
    assert set(placements) == {"pick_stations", "charging_dock", "buffer_tables"}
    assert len(placements["pick_stations"]) == scenario["device_counts"]["pick_station"]
    assert len(placements["buffer_tables"]) == scenario["device_counts"]["buffer_table"]
    assert isinstance(placements["charging_dock"], list)
    assert len(placements["charging_dock"]) == 2

    for coord in placements["pick_stations"] + placements["buffer_tables"] + [placements["charging_dock"]]:
        assert isinstance(coord, list)
        assert len(coord) == 2
        assert all(isinstance(value, int) for value in coord)

    assert_legal_layout(solution, scenario)

    expected_ids = {shelf["id"] for shelf in scenario["shelves"]}
    assert set(solution["shelf_service"]) == expected_ids

    expected_shelf_service, expected_total = evaluate_solution_payload(solution, scenario)
    assert solution["shelf_service"] == expected_shelf_service
    assert solution["total_service_score"] == expected_total

    optimal_total = find_optimal_total(scenario)
    _, actual_total = evaluate_solution_payload(solution, scenario)
    score = actual_total / optimal_total if optimal_total > 0 else 0.0
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(str(score))
    assert actual_total == optimal_total, (
        f"submitted total_service_score {actual_total} != optimal {optimal_total}"
    )


def main():
    run_checks()
    print("warehouse_service_layout verification passed")


if __name__ == "__main__":
    main()
