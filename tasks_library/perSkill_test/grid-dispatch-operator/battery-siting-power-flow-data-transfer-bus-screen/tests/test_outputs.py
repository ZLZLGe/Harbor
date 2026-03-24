import json
import os
from collections import defaultdict

import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/interconnection_screen.json")
NETWORK_FILE = os.environ.get("NETWORK_FILE", "/root/interconnection_network.json")
CANDIDATE_FILE = os.environ.get("CANDIDATE_FILE", "/root/candidate_buses.json")


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


@pytest.fixture(scope="module")
def screen():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def study():
    with open(CANDIDATE_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected(network, study):
    buses = network["bus"]
    gens = network["gen"]
    branches = network["branch"]
    thresholds = study["voltage_class_thresholds_kV"]

    bus_voltage = {int(row[0]): float(row[9]) for row in buses}
    positive_load = {int(row[0]): max(float(row[2]), 0.0) for row in buses}

    adjacency = defaultdict(set)
    connected_branch_count = defaultdict(int)
    transfer_capability = defaultdict(float)
    for row in branches:
        if int(row[10]) != 1:
            continue
        from_bus = int(row[0])
        to_bus = int(row[1])
        adjacency[from_bus].add(to_bus)
        adjacency[to_bus].add(from_bus)
        connected_branch_count[from_bus] += 1
        connected_branch_count[to_bus] += 1
        rating = float(row[5])
        if rating > 0:
            transfer_capability[from_bus] += rating
            transfer_capability[to_bus] += rating

    generation_headroom_by_bus = defaultdict(float)
    for row in gens:
        if int(row[7]) != 1:
            continue
        bus = int(row[0])
        generation_headroom_by_bus[bus] += max(float(row[8]) - float(row[1]), 0.0)

    def classify_voltage(voltage_kv):
        if voltage_kv >= float(thresholds["ehv_min"]):
            return "EHV", 3
        if voltage_kv >= float(thresholds["hv_min"]):
            return "HV", 2
        return "Subtransmission", 1

    ranked_buses = []
    for candidate in study["candidate_buses"]:
        bus = int(candidate)
        voltage_class, voltage_rank = classify_voltage(bus_voltage[bus])
        neighborhood = {bus, *adjacency[bus]}
        ranked_buses.append(
            {
                "bus": bus,
                "voltage_kV": round2(bus_voltage[bus]),
                "voltage_class": voltage_class,
                "voltage_class_rank": voltage_rank,
                "connected_in_service_branches": connected_branch_count[bus],
                "connected_branch_transfer_MW": round2(transfer_capability[bus]),
                "nearby_load_sink_MW": round2(
                    sum(positive_load.get(neighbor, 0.0) for neighbor in neighborhood)
                ),
                "local_generation_headroom_MW": round2(
                    sum(generation_headroom_by_bus.get(neighbor, 0.0) for neighbor in neighborhood)
                ),
            }
        )

    ranked_buses.sort(
        key=lambda row: (
            -row["voltage_class_rank"],
            -row["connected_branch_transfer_MW"],
            -row["nearby_load_sink_MW"],
            -row["local_generation_headroom_MW"],
            row["bus"],
        )
    )

    for index, row in enumerate(ranked_buses, start=1):
        row["rank"] = index

    return {
        "project_name": study["project_name"],
        "candidate_count": len(ranked_buses),
        "ranking_rule": {
            "primary": "voltage_class_rank_desc",
            "secondary": "connected_branch_transfer_MW_desc",
            "tertiary": "nearby_load_sink_MW_desc",
            "quaternary": "local_generation_headroom_MW_desc",
            "tie_breaker": "bus_asc",
        },
        "ranked_buses": ranked_buses,
    }


class TestSchema:
    def test_top_level_keys(self, screen):
        assert set(screen.keys()) == {
            "project_name",
            "candidate_count",
            "ranking_rule",
            "ranked_buses",
        }

    def test_ranking_rule_keys(self, screen):
        assert set(screen["ranking_rule"].keys()) == {
            "primary",
            "secondary",
            "tertiary",
            "quaternary",
            "tie_breaker",
        }

    def test_ranked_bus_keys(self, screen):
        expected_keys = {
            "rank",
            "bus",
            "voltage_kV",
            "voltage_class",
            "voltage_class_rank",
            "connected_in_service_branches",
            "connected_branch_transfer_MW",
            "nearby_load_sink_MW",
            "local_generation_headroom_MW",
        }
        for row in screen["ranked_buses"]:
            assert set(row.keys()) == expected_keys


class TestValues:
    def test_output_matches_expected(self, screen, expected):
        assert screen == expected

    def test_voltage_class_precedence(self, screen):
        buses = [row["bus"] for row in screen["ranked_buses"]]
        assert buses.index(1101) > buses.index(842)

    def test_top_candidate_and_bottom_candidate(self, screen):
        assert screen["ranked_buses"][0]["bus"] == 2633
        assert screen["ranked_buses"][-1]["bus"] == 1095

    def test_ranks_are_sequential(self, screen):
        assert [row["rank"] for row in screen["ranked_buses"]] == list(
            range(1, screen["candidate_count"] + 1)
        )
