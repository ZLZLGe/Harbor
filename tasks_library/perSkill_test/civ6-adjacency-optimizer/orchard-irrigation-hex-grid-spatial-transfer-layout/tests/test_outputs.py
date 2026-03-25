import json
import os
from itertools import combinations
from pathlib import Path

import pytest


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
SCENARIO_PATH = DATA_DIR / "orchard_plan.json"
OUTPUT_PATH = OUTPUT_DIR / "irrigation_layout.json"


def offset_to_cube(col, row):
    cube_x = col - (row - (row & 1)) // 2
    cube_z = row
    cube_y = -cube_x - cube_z
    return cube_x, cube_y, cube_z


def hex_distance(a, b):
    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def compute_coverage(scenario):
    radius = scenario["irrigation_radius"]
    coverage = {}
    for base in scenario["candidate_bases"]:
        base_id = base["id"]
        base_coord = (base["x"], base["y"])
        coverage[base_id] = sorted(
            crop["id"]
            for crop in scenario["crops"]
            if hex_distance(base_coord, (crop["x"], crop["y"])) <= radius
        )
    return coverage


def is_conflicting(base_ids, base_lookup, conflict_distance):
    for left, right in combinations(base_ids, 2):
        left_coord = (base_lookup[left]["x"], base_lookup[left]["y"])
        right_coord = (base_lookup[right]["x"], base_lookup[right]["y"])
        if hex_distance(left_coord, right_coord) <= conflict_distance:
            return True
    return False


def compute_expected_solution(scenario):
    base_lookup = {item["id"]: item for item in scenario["candidate_bases"]}
    sorted_base_ids = sorted(base_lookup)
    coverage = compute_coverage(scenario)
    crop_ids = [crop["id"] for crop in scenario["crops"]]
    conflict_distance = scenario["base_exclusion_distance"]

    chosen = None
    for size in range(1, len(sorted_base_ids) + 1):
        for candidate in combinations(sorted_base_ids, size):
            if is_conflicting(candidate, base_lookup, conflict_distance):
                continue
            covered = set()
            for base_id in candidate:
                covered.update(coverage[base_id])
            if covered == set(crop_ids):
                chosen = list(candidate)
                break
        if chosen is not None:
            break

    if chosen is None:
        raise AssertionError("输入场景没有可行解")

    expected = {
        "selected_bases": [
            {
                "base_id": base_id,
                "x": base_lookup[base_id]["x"],
                "y": base_lookup[base_id]["y"],
            }
            for base_id in chosen
        ],
        "base_coverages": [
            {
                "base_id": base_id,
                "covers": coverage[base_id],
            }
            for base_id in chosen
        ],
        "crop_coverages": [
            {
                "crop_id": crop["id"],
                "covered_by": [
                    base_id
                    for base_id in chosen
                    if crop["id"] in coverage[base_id]
                ],
            }
            for crop in scenario["crops"]
        ],
        "total_devices": len(chosen),
    }
    return expected, coverage, base_lookup


@pytest.fixture(scope="session")
def scenario():
    return json.loads(SCENARIO_PATH.read_text())


@pytest.fixture(scope="session")
def expected_bundle(scenario):
    return compute_expected_solution(scenario)


@pytest.fixture(scope="session")
def output():
    return json.loads(OUTPUT_PATH.read_text())


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"缺少输出文件: {OUTPUT_PATH}"


def test_top_level_schema(output):
    assert set(output.keys()) == {
        "selected_bases",
        "base_coverages",
        "crop_coverages",
        "total_devices",
    }
    assert isinstance(output["selected_bases"], list)
    assert isinstance(output["base_coverages"], list)
    assert isinstance(output["crop_coverages"], list)
    assert isinstance(output["total_devices"], int)


def test_selected_bases_schema_and_order(output, scenario):
    base_lookup = {item["id"]: item for item in scenario["candidate_bases"]}
    selected = output["selected_bases"]
    ids = []
    for item in selected:
        assert set(item.keys()) == {"base_id", "x", "y"}
        assert item["base_id"] in base_lookup
        assert isinstance(item["x"], int)
        assert isinstance(item["y"], int)
        expected = base_lookup[item["base_id"]]
        assert item["x"] == expected["x"]
        assert item["y"] == expected["y"]
        ids.append(item["base_id"])
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert output["total_devices"] == len(ids)


def test_base_coverages_schema(output):
    selected_ids = [item["base_id"] for item in output["selected_bases"]]
    base_coverages = output["base_coverages"]
    assert len(base_coverages) == len(selected_ids)
    assert [item["base_id"] for item in base_coverages] == selected_ids
    for item in base_coverages:
        assert set(item.keys()) == {"base_id", "covers"}
        assert isinstance(item["covers"], list)
        assert item["covers"] == sorted(item["covers"])


def test_crop_coverages_schema(output, scenario):
    crop_coverages = output["crop_coverages"]
    expected_crop_ids = [item["id"] for item in scenario["crops"]]
    assert len(crop_coverages) == len(expected_crop_ids)
    assert [item["crop_id"] for item in crop_coverages] == expected_crop_ids
    for item in crop_coverages:
        assert set(item.keys()) == {"crop_id", "covered_by"}
        assert isinstance(item["covered_by"], list)
        assert item["covered_by"] == sorted(item["covered_by"])


def test_selected_bases_are_non_adjacent(output, scenario):
    base_lookup = {item["id"]: item for item in scenario["candidate_bases"]}
    conflict_distance = scenario["base_exclusion_distance"]
    selected_ids = [item["base_id"] for item in output["selected_bases"]]
    assert not is_conflicting(selected_ids, base_lookup, conflict_distance)


def test_coverages_match_geometry(output, scenario, expected_bundle):
    _, coverage, _ = expected_bundle
    selected_ids = [item["base_id"] for item in output["selected_bases"]]

    expected_base_coverages = [
        {"base_id": base_id, "covers": coverage[base_id]}
        for base_id in selected_ids
    ]
    assert output["base_coverages"] == expected_base_coverages

    expected_crop_coverages = [
        {
            "crop_id": crop["id"],
            "covered_by": [
                base_id
                for base_id in selected_ids
                if crop["id"] in coverage[base_id]
            ],
        }
        for crop in scenario["crops"]
    ]
    assert output["crop_coverages"] == expected_crop_coverages
    assert all(item["covered_by"] for item in output["crop_coverages"])


def test_solution_is_optimal_and_tie_broken(output, expected_bundle):
    expected, _, _ = expected_bundle
    assert output["selected_bases"] == expected["selected_bases"]
    assert output["base_coverages"] == expected["base_coverages"]
    assert output["crop_coverages"] == expected["crop_coverages"]
    assert output["total_devices"] == expected["total_devices"]
