import json
import os
from collections import defaultdict, deque

import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/island_assessment.json")
NETWORK_FILE = os.environ.get("INPUT_NETWORK", "/root/network.json")
OUTAGE_FILE = os.environ.get("INPUT_OUTAGES", "/root/outages.json")
EXPECTED_LOAD_RULE = "effective_load_mw = max(Pd, 0)"


def round2(value):
    return round(float(value), 2)


@pytest.fixture(scope="module")
def actual_output():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def outages():
    with open(OUTAGE_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_output(network, outages):
    buses = network["bus"]
    gens = network["gen"]
    branches = network["branch"]
    reserve_capacity = network["reserve_capacity"]

    bus_numbers = sorted(int(row[0]) for row in buses)
    bus_by_number = {int(row[0]): row for row in buses}
    removed_branch_indices = [int(idx) for idx in outages["outaged_branch_indices"]]
    removed_branch_set = set(removed_branch_indices)
    critical_bus_set = {int(bus) for bus in outages["critical_buses"]}

    adjacency = defaultdict(set)
    for branch_index, branch in enumerate(branches):
        if int(branch[10]) != 1 or branch_index in removed_branch_set:
            continue
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        adjacency[from_bus].add(to_bus)
        adjacency[to_bus].add(from_bus)

    generation_capacity_by_bus = defaultdict(float)
    reserve_capacity_by_bus = defaultdict(float)
    for gen_index, gen in enumerate(gens):
        if int(gen[7]) != 1:
            continue
        bus_number = int(gen[0])
        generation_capacity_by_bus[bus_number] += float(gen[8])
        reserve_capacity_by_bus[bus_number] += float(reserve_capacity[gen_index])

    islands = []
    visited = set()
    for start_bus in bus_numbers:
        if start_bus in visited:
            continue

        queue = deque([start_bus])
        visited.add(start_bus)
        component = []

        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)

        component.sort()
        has_reference_bus = any(int(bus_by_number[bus][1]) == 3 for bus in component)
        islands.append(
            {
                "bus_numbers": component,
                "bus_count": len(component),
                "total_effective_load_mw": round2(
                    sum(max(float(bus_by_number[bus][2]), 0.0) for bus in component)
                ),
                "total_generation_capacity_mw": round2(
                    sum(generation_capacity_by_bus[bus] for bus in component)
                ),
                "total_reserve_capacity_mw": round2(
                    sum(reserve_capacity_by_bus[bus] for bus in component)
                ),
                "has_reference_bus": has_reference_bus,
                "disconnected_critical_buses": (
                    sorted(bus for bus in component if bus in critical_bus_set)
                    if not has_reference_bus
                    else []
                ),
            }
        )

    islands.sort(key=lambda item: item["bus_numbers"][0])
    for index, island in enumerate(islands, start=1):
        island["island_id"] = f"island_{index}"

    return {
        "network_name": network["name"],
        "outage_scenario": outages["scenario_name"],
        "removed_branch_indices": removed_branch_indices,
        "island_count": len(islands),
        "load_rule": EXPECTED_LOAD_RULE,
        "islands": islands,
    }


def test_top_level_schema(actual_output, expected_output):
    assert set(actual_output.keys()) == set(expected_output.keys())
    assert actual_output["network_name"] == expected_output["network_name"]
    assert actual_output["outage_scenario"] == expected_output["outage_scenario"]
    assert actual_output["removed_branch_indices"] == expected_output["removed_branch_indices"]
    assert actual_output["island_count"] == expected_output["island_count"]
    assert actual_output["load_rule"] == EXPECTED_LOAD_RULE
    assert isinstance(actual_output["islands"], list)


def test_island_assessment_matches_expected(actual_output, expected_output):
    assert actual_output == expected_output


def test_disconnected_critical_buses_follow_rule(actual_output):
    for island in actual_output["islands"]:
        if island["has_reference_bus"]:
            assert island["disconnected_critical_buses"] == []
        else:
            assert island["disconnected_critical_buses"] == sorted(
                island["disconnected_critical_buses"]
            )
