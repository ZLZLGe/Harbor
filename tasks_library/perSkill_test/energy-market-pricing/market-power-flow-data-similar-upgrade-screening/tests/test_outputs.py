import json
import os
from collections import defaultdict

import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/constraint_screening.json")
NETWORK_FILE = os.environ.get("INPUT_NETWORK", "/root/network.json")
CANDIDATE_FILE = os.environ.get("INPUT_CANDIDATES", "/root/candidate_constraints.json")

BUS_TYPE_LABELS = {
    1: "PQ",
    2: "PV",
    3: "REF",
    4: "NONE",
}

EXPECTED_EFFECTIVE_LOAD_RULE = "effective_load_mw = max(Pd, 0)"
EXPECTED_SCORE_FORMULA = (
    "combined_one_hop_effective_load_mw / line_rating_mw + "
    "0.1 * (from_bus_degree + to_bus_degree) + "
    "0.5 * controllable_endpoint_count - "
    "0.0002 * combined_one_hop_generation_capacity_mw - "
    "0.0005 * combined_one_hop_reserve_capacity_mw"
)


def round2(value):
    return round(float(value), 2)


def round6(value):
    return round(float(value), 6)


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
def candidates():
    with open(CANDIDATE_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_output(network, candidates):
    buses = network["bus"]
    gens = network["gen"]
    branches = network["branch"]
    reserve_capacity = network["reserve_capacity"]

    bus_by_number = {int(row[0]): row for row in buses}
    adjacency = defaultdict(set)
    for branch in branches:
        if int(branch[10]) != 1:
            continue
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        adjacency[from_bus].add(to_bus)
        adjacency[to_bus].add(from_bus)

    generation_capacity_by_bus = defaultdict(float)
    reserve_capacity_by_bus = defaultdict(float)
    for idx, gen in enumerate(gens):
        if int(gen[7]) != 1:
            continue
        bus_number = int(gen[0])
        generation_capacity_by_bus[bus_number] += float(gen[8])
        reserve_capacity_by_bus[bus_number] += float(reserve_capacity[idx])

    def effective_load(bus_number):
        return max(float(bus_by_number[bus_number][2]), 0.0)

    def endpoint_summary(bus_number):
        return {
            "effective_load_mw": round2(effective_load(bus_number)),
            "generation_capacity_mw": round2(generation_capacity_by_bus[bus_number]),
            "reserve_capacity_mw": round6(reserve_capacity_by_bus[bus_number]),
        }

    def one_hop_set(bus_number):
        return {bus_number} | set(adjacency[bus_number])

    def neighborhood_summary(bus_numbers):
        nodes = sorted(bus_numbers)
        return {
            "bus_count": len(nodes),
            "effective_load_mw": round2(sum(effective_load(bus) for bus in nodes)),
            "generation_capacity_mw": round2(
                sum(generation_capacity_by_bus[bus] for bus in nodes)
            ),
            "reserve_capacity_mw": round6(
                sum(reserve_capacity_by_bus[bus] for bus in nodes)
            ),
        }

    def bus_type(bus_number):
        code = int(bus_by_number[bus_number][1])
        return {"code": code, "label": BUS_TYPE_LABELS[code]}

    screened_constraints = []
    for candidate in candidates["candidates"]:
        branch_index = int(candidate["branch_index"])
        branch = branches[branch_index]
        from_bus = int(branch[0])
        to_bus = int(branch[1])

        from_one_hop = one_hop_set(from_bus)
        to_one_hop = one_hop_set(to_bus)
        combined_one_hop = from_one_hop | to_one_hop
        from_degree = len(adjacency[from_bus])
        to_degree = len(adjacency[to_bus])
        controllable_endpoint_count = sum(
            1 for bus in (from_bus, to_bus) if int(bus_by_number[bus][1]) in (2, 3)
        )
        combined_summary = neighborhood_summary(combined_one_hop)
        line_rating_mw = round2(branch[5])

        exposure_score = round6(
            combined_summary["effective_load_mw"] / line_rating_mw
            + 0.1 * (from_degree + to_degree)
            + 0.5 * controllable_endpoint_count
            - 0.0002 * combined_summary["generation_capacity_mw"]
            - 0.0005 * combined_summary["reserve_capacity_mw"]
        )

        screened_constraints.append(
            {
                "constraint_id": candidate["constraint_id"],
                "branch_index": branch_index,
                "from_bus": from_bus,
                "to_bus": to_bus,
                "line_rating_mw": line_rating_mw,
                "from_bus_type": bus_type(from_bus),
                "to_bus_type": bus_type(to_bus),
                "from_bus_degree": from_degree,
                "to_bus_degree": to_degree,
                "from_endpoint_summary": endpoint_summary(from_bus),
                "to_endpoint_summary": endpoint_summary(to_bus),
                "from_one_hop_summary": neighborhood_summary(from_one_hop),
                "to_one_hop_summary": neighborhood_summary(to_one_hop),
                "combined_one_hop_summary": combined_summary,
                "controllable_endpoint_count": controllable_endpoint_count,
                "exposure_score": exposure_score,
            }
        )

    screened_constraints.sort(
        key=lambda item: (-item["exposure_score"], item["constraint_id"])
    )
    for rank, item in enumerate(screened_constraints, start=1):
        item["priority_rank"] = rank

    return {
        "network_name": network["name"],
        "candidate_dataset": candidates["dataset_name"],
        "candidate_count": len(screened_constraints),
        "effective_load_rule": EXPECTED_EFFECTIVE_LOAD_RULE,
        "score_formula": EXPECTED_SCORE_FORMULA,
        "screened_constraints": screened_constraints,
    }


def test_top_level_schema(actual_output, expected_output):
    assert set(actual_output.keys()) == set(expected_output.keys())
    assert actual_output["network_name"] == expected_output["network_name"]
    assert actual_output["candidate_dataset"] == expected_output["candidate_dataset"]
    assert actual_output["candidate_count"] == expected_output["candidate_count"]
    assert actual_output["effective_load_rule"] == EXPECTED_EFFECTIVE_LOAD_RULE
    assert actual_output["score_formula"] == EXPECTED_SCORE_FORMULA
    assert isinstance(actual_output["screened_constraints"], list)


def test_screened_constraints_match_expected(actual_output, expected_output):
    assert actual_output["screened_constraints"] == expected_output["screened_constraints"]


def test_ranking_and_scores_are_consistent(actual_output):
    constraints = actual_output["screened_constraints"]
    assert constraints, "screened_constraints should not be empty"

    observed_ranks = [item["priority_rank"] for item in constraints]
    assert observed_ranks == list(range(1, len(constraints) + 1))

    sorted_copy = sorted(
        constraints,
        key=lambda item: (-item["exposure_score"], item["constraint_id"]),
    )
    assert constraints == sorted_copy
