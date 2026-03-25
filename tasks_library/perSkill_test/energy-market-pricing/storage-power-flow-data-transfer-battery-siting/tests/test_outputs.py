import csv
import json
import os
from collections import defaultdict

import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "battery_site_ranking.csv")
NETWORK_FILE = os.environ.get("INPUT_NETWORK", "network.json")
CANDIDATE_FILE = os.environ.get("INPUT_CANDIDATES", "candidate_sites.csv")

FIELDNAMES = [
    "candidate_id",
    "site_name",
    "interconnection_bus",
    "connected_bus_degree",
    "connectivity_label",
    "two_hop_bus_count",
    "two_hop_effective_load_mw",
    "adjacent_line_rating_sum_mw",
    "same_bus_generation_capacity_mw",
    "same_bus_available_reserve_mw",
    "screening_score",
    "priority_rank",
]


def format2(value):
    return f"{float(value):.2f}"


def format6(value):
    return f"{float(value):.6f}"


def connectivity_label(degree):
    if degree == 0:
        return "isolated"
    if degree == 1:
        return "radial"
    if degree <= 3:
        return "corridor"
    return "hub"


@pytest.fixture(scope="module")
def actual_output():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames, rows


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def candidates():
    with open(CANDIDATE_FILE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def expected_rows(network, candidates):
    bus_by_number = {int(row[0]): row for row in network["bus"]}
    adjacency = defaultdict(set)
    adjacent_line_rating_sum = defaultdict(float)

    for branch in network["branch"]:
        if int(branch[10]) != 1:
            continue
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        rate_a = float(branch[5])
        adjacency[from_bus].add(to_bus)
        adjacency[to_bus].add(from_bus)
        adjacent_line_rating_sum[from_bus] += rate_a
        adjacent_line_rating_sum[to_bus] += rate_a

    generation_capacity_by_bus = defaultdict(float)
    reserve_capacity_by_bus = defaultdict(float)
    for gen_index, gen in enumerate(network["gen"]):
        if int(gen[7]) != 1:
            continue
        bus_number = int(gen[0])
        generation_capacity_by_bus[bus_number] += float(gen[8])
        reserve_capacity_by_bus[bus_number] += float(network["reserve_capacity"][gen_index])

    def effective_load(bus_number):
        return max(float(bus_by_number[bus_number][2]), 0.0)

    def two_hop_buses(start_bus):
        visited = {start_bus}
        frontier = {start_bus}
        for _ in range(2):
            next_frontier = set()
            for bus_number in frontier:
                next_frontier.update(adjacency[bus_number])
            frontier = next_frontier - visited
            visited.update(next_frontier)
        return visited

    rows = []
    for candidate in candidates:
        bus_number = int(candidate["interconnection_bus"])
        degree = len(adjacency[bus_number])
        nearby_buses = two_hop_buses(bus_number)
        two_hop_effective_load = sum(effective_load(bus) for bus in nearby_buses)
        same_bus_generation_capacity = generation_capacity_by_bus[bus_number]
        same_bus_available_reserve = reserve_capacity_by_bus[bus_number]
        score = (
            two_hop_effective_load / 100.0
            + adjacent_line_rating_sum[bus_number] / 5000.0
            + same_bus_available_reserve / 10.0
            - same_bus_generation_capacity / 200.0
        )

        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "site_name": candidate["site_name"],
                "interconnection_bus": str(bus_number),
                "connected_bus_degree": str(degree),
                "connectivity_label": connectivity_label(degree),
                "two_hop_bus_count": str(len(nearby_buses)),
                "two_hop_effective_load_mw": format2(two_hop_effective_load),
                "adjacent_line_rating_sum_mw": format2(adjacent_line_rating_sum[bus_number]),
                "same_bus_generation_capacity_mw": format2(same_bus_generation_capacity),
                "same_bus_available_reserve_mw": format2(same_bus_available_reserve),
                "screening_score": format6(score),
            }
        )

    rows.sort(key=lambda row: (-float(row["screening_score"]), row["candidate_id"]))
    for rank, row in enumerate(rows, start=1):
        row["priority_rank"] = str(rank)

    return rows


def test_csv_header_and_row_count(actual_output, candidates):
    fieldnames, rows = actual_output
    assert fieldnames == FIELDNAMES
    assert len(rows) == len(candidates)


def test_rows_match_expected(actual_output, expected_rows):
    _, rows = actual_output
    assert rows == expected_rows


def test_ranking_and_labels_are_consistent(actual_output):
    _, rows = actual_output
    assert rows, "battery_site_ranking.csv should contain at least one row"

    observed_ranks = [int(row["priority_rank"]) for row in rows]
    assert observed_ranks == list(range(1, len(rows) + 1))

    sorted_rows = sorted(
        rows,
        key=lambda row: (-float(row["screening_score"]), row["candidate_id"]),
    )
    assert rows == sorted_rows

    for row in rows:
        degree = int(row["connected_bus_degree"])
        assert row["connectivity_label"] == connectivity_label(degree)
