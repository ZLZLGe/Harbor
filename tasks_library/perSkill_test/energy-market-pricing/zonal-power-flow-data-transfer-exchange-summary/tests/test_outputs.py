import json
import os
from collections import defaultdict

import pytest

OUTPUT_FILE = "/root/zone_exchange_summary.json"
NETWORK_FILE = "/root/network.json"
ZONES_FILE = "/root/zones.json"


def round2(value):
    return round(float(value), 2)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def output_data():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    return load_json(OUTPUT_FILE)


@pytest.fixture(scope="module")
def network():
    return load_json(NETWORK_FILE)


@pytest.fixture(scope="module")
def zone_data():
    return load_json(ZONES_FILE)


@pytest.fixture(scope="module")
def expected(network, zone_data):
    zone_order = [item["zone_id"] for item in zone_data["zone_definitions"]]
    zone_name_by_id = {item["zone_id"]: item["zone_name"] for item in zone_data["zone_definitions"]}
    bus_to_zone = {int(bus): zone_id for bus, zone_id in zone_data["bus_to_zone"].items()}

    bus_rows = {int(row[0]): row for row in network["bus"]}
    zone_buses = {zone_id: [] for zone_id in zone_order}
    for row in network["bus"]:
        bus_number = int(row[0])
        zone_buses[bus_to_zone[bus_number]].append(bus_number)

    zone_generation_capacity = defaultdict(float)
    zone_reserve_capacity = defaultdict(float)
    for index, gen in enumerate(network["gen"]):
        if int(gen[7]) != 1:
            continue
        zone_id = bus_to_zone[int(gen[0])]
        zone_generation_capacity[zone_id] += float(gen[8])
        zone_reserve_capacity[zone_id] += float(network["reserve_capacity"][index])

    zones = []
    for zone_id in zone_order:
        reference_bus_numbers = sorted(
            bus_number
            for bus_number in zone_buses[zone_id]
            if int(bus_rows[bus_number][1]) == 3
        )
        total_effective_load = sum(max(float(bus_rows[bus_number][2]), 0.0) for bus_number in zone_buses[zone_id])
        zones.append(
            {
                "zone_id": zone_id,
                "zone_name": zone_name_by_id[zone_id],
                "bus_count": len(zone_buses[zone_id]),
                "total_effective_load_mw": round2(total_effective_load),
                "total_generation_capacity_mw": round2(zone_generation_capacity[zone_id]),
                "total_reserve_capacity_mw": round2(zone_reserve_capacity[zone_id]),
                "reference_bus_numbers": reference_bus_numbers,
                "has_reference_bus": bool(reference_bus_numbers),
            }
        )

    interface_totals = defaultdict(lambda: {"active_branch_count": 0, "total_rating_mw": 0.0})
    for branch in network["branch"]:
        if int(branch[10]) != 1:
            continue
        zone_a = bus_to_zone[int(branch[0])]
        zone_b = bus_to_zone[int(branch[1])]
        if zone_a == zone_b:
            continue
        from_zone, to_zone = sorted((zone_a, zone_b))
        interface_totals[(from_zone, to_zone)]["active_branch_count"] += 1
        interface_totals[(from_zone, to_zone)]["total_rating_mw"] += float(branch[5])

    interzonal_interfaces = []
    for from_zone, to_zone in sorted(interface_totals):
        totals = interface_totals[(from_zone, to_zone)]
        interzonal_interfaces.append(
            {
                "interface_id": f"{from_zone}__{to_zone}",
                "from_zone": from_zone,
                "to_zone": to_zone,
                "active_branch_count": totals["active_branch_count"],
                "total_rating_mw": round2(totals["total_rating_mw"]),
            }
        )

    return {
        "network_name": network["name"],
        "zone_dataset": zone_data["dataset_name"],
        "zone_count": len(zones),
        "interzonal_interface_count": len(interzonal_interfaces),
        "effective_load_rule": "effective_load_mw = max(Pd, 0)",
        "zones": zones,
        "interzonal_interfaces": interzonal_interfaces,
    }


class TestSchema:
    def test_top_level_fields(self, output_data):
        assert sorted(output_data.keys()) == sorted(
            [
                "network_name",
                "zone_dataset",
                "zone_count",
                "interzonal_interface_count",
                "effective_load_rule",
                "zones",
                "interzonal_interfaces",
            ]
        )

    def test_zone_entries_shape(self, output_data):
        assert isinstance(output_data["zones"], list)
        for zone in output_data["zones"]:
            assert sorted(zone.keys()) == sorted(
                [
                    "zone_id",
                    "zone_name",
                    "bus_count",
                    "total_effective_load_mw",
                    "total_generation_capacity_mw",
                    "total_reserve_capacity_mw",
                    "reference_bus_numbers",
                    "has_reference_bus",
                ]
            )
            assert isinstance(zone["reference_bus_numbers"], list)
            assert isinstance(zone["has_reference_bus"], bool)

    def test_interface_entries_shape(self, output_data):
        assert isinstance(output_data["interzonal_interfaces"], list)
        for interface in output_data["interzonal_interfaces"]:
            assert sorted(interface.keys()) == sorted(
                [
                    "interface_id",
                    "from_zone",
                    "to_zone",
                    "active_branch_count",
                    "total_rating_mw",
                ]
            )


class TestSemantics:
    def test_output_matches_expected(self, output_data, expected):
        assert output_data == expected

    def test_zone_order_matches_definition_order(self, output_data, zone_data):
        expected_order = [item["zone_id"] for item in zone_data["zone_definitions"]]
        assert [item["zone_id"] for item in output_data["zones"]] == expected_order

    def test_interface_sorting_and_canonical_pairs(self, output_data):
        pairs = [(item["from_zone"], item["to_zone"]) for item in output_data["interzonal_interfaces"]]
        assert pairs == sorted(pairs)
        for interface in output_data["interzonal_interfaces"]:
            assert interface["from_zone"] < interface["to_zone"]
            assert interface["interface_id"] == f"{interface['from_zone']}__{interface['to_zone']}"

    def test_numeric_fields_are_rounded_to_two_decimals(self, output_data):
        for zone in output_data["zones"]:
            assert zone["total_effective_load_mw"] == round2(zone["total_effective_load_mw"])
            assert zone["total_generation_capacity_mw"] == round2(zone["total_generation_capacity_mw"])
            assert zone["total_reserve_capacity_mw"] == round2(zone["total_reserve_capacity_mw"])
        for interface in output_data["interzonal_interfaces"]:
            assert interface["total_rating_mw"] == round2(interface["total_rating_mw"])
