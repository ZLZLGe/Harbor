import json
import os
from collections import deque

import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/islanding_triage.json")
NETWORK_FILE = os.environ.get("NETWORK_FILE", "/root/storm_network.json")
OUTAGE_FILE = os.environ.get("OUTAGE_FILE", "/root/storm_outages.json")


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


def normalize_pair(a, b):
    first = int(a)
    second = int(b)
    return (first, second) if first < second else (second, first)


@pytest.fixture(scope="module")
def triage():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
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
def expected(network, outages):
    buses = network["bus"]
    gens = network["gen"]
    branches = network["branch"]

    bus_numbers = sorted(int(row[0]) for row in buses)
    bus_loads = {int(row[0]): float(row[2]) for row in buses}

    generation_by_bus = {bus: 0.0 for bus in bus_numbers}
    for row in gens:
        if int(row[7]) != 1:
            continue
        generation_by_bus[int(row[0])] = generation_by_bus.get(int(row[0]), 0.0) + float(row[8])

    outage_pairs = sorted(
        {normalize_pair(line["from"], line["to"]) for line in outages["outaged_lines"]}
    )
    outage_set = set(outage_pairs)

    adjacency = {bus: set() for bus in bus_numbers}
    for row in branches:
        if int(row[10]) != 1:
            continue
        pair = normalize_pair(row[0], row[1])
        if pair in outage_set:
            continue
        a, b = pair
        adjacency[a].add(b)
        adjacency[b].add(a)

    components = []
    seen = set()
    for bus in bus_numbers:
        if bus in seen:
            continue
        queue = deque([bus])
        seen.add(bus)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))

    components.sort(key=lambda rows: rows[0])

    islands = []
    for island_id, component in enumerate(components, start=1):
        component_set = set(component)
        stranded_load = sum(bus_loads[bus] for bus in component)
        surviving_generation = sum(generation_by_bus.get(bus, 0.0) for bus in component)
        responsible_outage_lines = [
            {"from": pair[0], "to": pair[1]}
            for pair in outage_pairs
            if (pair[0] in component_set) ^ (pair[1] in component_set)
        ]
        islands.append(
            {
                "island_id": island_id,
                "isolated_buses": component,
                "stranded_load_MW": round2(stranded_load),
                "surviving_generation_MW": round2(surviving_generation),
                "generation_minus_load_MW": round2(surviving_generation - stranded_load),
                "responsible_outage_lines": responsible_outage_lines,
            }
        )

    return {
        "island_count": len(islands),
        "totals": {
            "stranded_load_MW": round2(sum(bus_loads.values())),
            "surviving_generation_MW": round2(sum(generation_by_bus.values())),
        },
        "islands": islands,
    }


class TestSchema:
    def test_top_level_keys(self, triage):
        assert set(triage.keys()) == {"island_count", "totals", "islands"}

    def test_totals_keys(self, triage):
        assert set(triage["totals"].keys()) == {"stranded_load_MW", "surviving_generation_MW"}

    def test_island_keys(self, triage):
        expected_keys = {
            "island_id",
            "isolated_buses",
            "stranded_load_MW",
            "surviving_generation_MW",
            "generation_minus_load_MW",
            "responsible_outage_lines",
        }
        for island in triage["islands"]:
            assert set(island.keys()) == expected_keys


class TestValues:
    def test_output_matches_expected(self, triage, expected):
        assert triage == expected

    def test_singleton_island_exists(self, triage):
        singleton = next(island for island in triage["islands"] if island["isolated_buses"] == [511])
        assert singleton["stranded_load_MW"] == 39.5
        assert singleton["surviving_generation_MW"] == 0.0
        assert singleton["responsible_outage_lines"] == [
            {"from": 309, "to": 511},
            {"from": 402, "to": 511},
            {"from": 511, "to": 620},
        ]

    def test_islands_sorted_by_smallest_bus(self, triage):
        starts = [island["isolated_buses"][0] for island in triage["islands"]]
        assert starts == sorted(starts)
