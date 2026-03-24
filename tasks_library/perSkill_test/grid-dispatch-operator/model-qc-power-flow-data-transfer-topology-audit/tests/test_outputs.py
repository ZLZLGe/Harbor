import json
import os

import pytest

OUTPUT_FILE = "/root/topology_audit.json"
NETWORK_FILE = "/root/qc_network.json"


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


@pytest.fixture(scope="module")
def audit():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected(network):
    buses = network["bus"]
    gens = network["gen"]
    branches = network["branch"]

    bus_numbers = sorted(int(row[0]) for row in buses)
    bus_set = set(bus_numbers)
    bus_by_number = {int(row[0]): row for row in buses}

    normalized_bus_index_map = [
        {"bus": bus, "normalized_index": index}
        for index, bus in enumerate(bus_numbers)
    ]

    incident_counts = {bus: 0 for bus in bus_numbers}
    active_corridors = {}
    zero_reactance = []
    zero_rating = []
    in_service_branch_count = 0

    for row_id, branch in enumerate(branches, start=1):
        if int(branch[10]) != 1:
            continue

        in_service_branch_count += 1
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        norm_from, norm_to = sorted((from_bus, to_bus))
        incident_counts[norm_from] += 1
        incident_counts[norm_to] += 1
        active_corridors.setdefault((norm_from, norm_to), []).append(row_id)

        reactance = float(branch[3])
        rate_a = float(branch[5])
        anomaly_row = {
            "branch_row_id": row_id,
            "from": norm_from,
            "to": norm_to,
            "reactance_pu": round2(reactance),
            "rate_a_MVA": round2(rate_a),
        }
        if reactance == 0.0:
            zero_reactance.append(anomaly_row)
        if rate_a <= 0.0:
            zero_rating.append(anomaly_row)

    orphan_buses = [
        {
            "bus": bus,
            "bus_type": int(bus_by_number[bus][1]),
            "pd_MW": round2(bus_by_number[bus][2]),
        }
        for bus in bus_numbers
        if incident_counts[bus] == 0
    ]

    duplicate_corridors = [
        {
            "from": pair[0],
            "to": pair[1],
            "branch_row_ids": row_ids,
            "in_service_branch_count": len(row_ids),
        }
        for pair, row_ids in sorted(active_corridors.items())
        if len(row_ids) >= 2
    ]

    invalid_generator_bus_references = [
        {
            "generator_row_id": row_id,
            "bus": int(gen[0]),
            "gen_status": int(gen[7]),
        }
        for row_id, gen in enumerate(gens, start=1)
        if int(gen[0]) not in bus_set
    ]

    return {
        "snapshot_name": network["name"],
        "summary": {
            "bus_count": len(buses),
            "generator_count": len(gens),
            "branch_count": len(branches),
            "in_service_branch_count": in_service_branch_count,
            "orphan_bus_count": len(orphan_buses),
            "duplicate_corridor_count": len(duplicate_corridors),
            "zero_reactance_count": len(zero_reactance),
            "zero_rating_count": len(zero_rating),
            "invalid_generator_reference_count": len(invalid_generator_bus_references),
        },
        "normalized_bus_index_map": normalized_bus_index_map,
        "orphan_buses": orphan_buses,
        "duplicate_corridors": duplicate_corridors,
        "branch_anomalies": {
            "zero_reactance": zero_reactance,
            "zero_rating": zero_rating,
        },
        "invalid_generator_bus_references": invalid_generator_bus_references,
    }


class TestSchema:
    def test_top_level_keys(self, audit):
        assert set(audit.keys()) == {
            "snapshot_name",
            "summary",
            "normalized_bus_index_map",
            "orphan_buses",
            "duplicate_corridors",
            "branch_anomalies",
            "invalid_generator_bus_references",
        }

    def test_summary_keys(self, audit):
        assert set(audit["summary"].keys()) == {
            "bus_count",
            "generator_count",
            "branch_count",
            "in_service_branch_count",
            "orphan_bus_count",
            "duplicate_corridor_count",
            "zero_reactance_count",
            "zero_rating_count",
            "invalid_generator_reference_count",
        }

    def test_branch_anomaly_keys(self, audit):
        assert set(audit["branch_anomalies"].keys()) == {"zero_reactance", "zero_rating"}


class TestValues:
    def test_output_matches_expected(self, audit, expected):
        assert audit == expected

    def test_orphan_bus_with_generator_is_retained(self, audit):
        orphan_buses = [row["bus"] for row in audit["orphan_buses"]]
        assert orphan_buses == [511, 730]

    def test_duplicate_corridor_and_invalid_generator_pattern(self, audit):
        assert audit["duplicate_corridors"] == [
            {"from": 101, "to": 205, "branch_row_ids": [1, 3], "in_service_branch_count": 2}
        ]
        assert audit["invalid_generator_bus_references"] == [
            {"generator_row_id": 4, "bus": 999, "gen_status": 1}
        ]

    def test_normalized_bus_map_is_contiguous(self, audit):
        indices = [row["normalized_index"] for row in audit["normalized_bus_index_map"]]
        assert indices == list(range(len(indices)))
