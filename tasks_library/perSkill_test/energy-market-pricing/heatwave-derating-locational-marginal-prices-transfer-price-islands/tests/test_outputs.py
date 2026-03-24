import json
import os

import pytest

OUTPUT_FILE = "/root/price_island_risk.json"
NETWORK_FILE = "/root/compact_heatwave_network.json"
EVENT_FILE = "/root/heatwave_event.json"


def round2(value):
    return round(float(value) + 1e-9, 2)


@pytest.fixture(scope="module")
def output():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def event():
    with open(EVENT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference(network, event):
    bus_load = {int(row[0]): float(row[2]) for row in network["bus"]}
    branch_limits = {(int(row[0]), int(row[1])): float(row[5]) for row in network["branch"]}
    cost_by_bus = {
        int(network["gen"][idx][0]): float(network["gencost"][idx][5])
        for idx in range(len(network["gen"]))
    }
    pmax_by_bus = {int(row[0]): float(row[8]) for row in network["gen"]}
    reserve_capacity = {
        int(network["gen"][idx][0]): float(network["reserve_capacity"][idx])
        for idx in range(len(network["gen"]))
    }
    reserve_requirement = float(network["reserve_requirement"])

    def get_limit(from_bus, to_bus, overrides):
        if (from_bus, to_bus) in overrides:
            return overrides[(from_bus, to_bus)]
        if (to_bus, from_bus) in overrides:
            return overrides[(to_bus, from_bus)]
        if (from_bus, to_bus) in branch_limits:
            return branch_limits[(from_bus, to_bus)]
        return branch_limits[(to_bus, from_bus)]

    def solve_case(case_id, overrides):
        limit_629_64 = get_limit(629, 64, overrides)
        limit_64_1501 = get_limit(64, 1501, overrides)

        local_1501 = max(0.0, bus_load[1501] - limit_64_1501)
        local_64 = max(0.0, bus_load[64] + bus_load[1501] - local_1501 - limit_629_64)
        import_to_1501 = bus_load[1501] - local_1501
        import_to_64_pocket = bus_load[64] + import_to_1501 - local_64
        upstream_need = bus_load[672] + bus_load[629] + import_to_64_pocket

        g1 = min(pmax_by_bus[2615], upstream_need)
        g2 = upstream_need - g1
        g3 = local_64
        g4 = local_1501

        assert g2 <= pmax_by_bus[672] + 1e-9
        assert g3 <= pmax_by_bus[64] + 1e-9
        assert g4 <= pmax_by_bus[1501] + 1e-9

        reserve_headroom = (
            min(reserve_capacity[2615], pmax_by_bus[2615] - g1)
            + min(reserve_capacity[672], pmax_by_bus[672] - g2)
            + min(reserve_capacity[64], pmax_by_bus[64] - g3)
            + min(reserve_capacity[1501], pmax_by_bus[1501] - g4)
        )
        assert reserve_headroom + 1e-9 >= reserve_requirement

        left_lmp = cost_by_bus[672] if g2 > 1e-9 else cost_by_bus[2615]
        bus64_lmp = cost_by_bus[64] if g3 > 1e-9 else left_lmp
        bus1501_lmp = cost_by_bus[1501] if g4 > 1e-9 else bus64_lmp

        lmp_map = {
            2: left_lmp,
            64: bus64_lmp,
            629: left_lmp,
            672: left_lmp,
            1501: bus1501_lmp,
            2615: left_lmp,
        }
        flows = {
            (2615, 2): g1,
            (2, 672): g1,
            (672, 629): bus_load[629] + import_to_64_pocket,
            (629, 64): import_to_64_pocket,
            (64, 1501): import_to_1501,
        }
        binding_lines = []
        for row in network["branch"]:
            from_bus = int(row[0])
            to_bus = int(row[1])
            limit = get_limit(from_bus, to_bus, overrides)
            flow = flows[(from_bus, to_bus)]
            loading_pct = abs(flow) / limit * 100.0
            if loading_pct + 1e-9 >= float(event["binding_threshold_pct"]):
                binding_lines.append(
                    {
                        "from": from_bus,
                        "to": to_bus,
                        "flow_MW": round2(flow),
                        "limit_MW": round2(limit),
                        "loading_pct": round2(loading_pct),
                    }
                )
        binding_lines.sort(key=lambda item: (item["from"], item["to"]))

        total_cost = (
            g1 * cost_by_bus[2615]
            + g2 * cost_by_bus[672]
            + g3 * cost_by_bus[64]
            + g4 * cost_by_bus[1501]
        )
        return {
            "scenario_id": case_id,
            "total_cost_dollars_per_hour": round2(total_cost),
            "reserve_mcp_dollars_per_MWh": 0.0,
            "lmp_by_bus": [
                {"bus": bus, "lmp_dollars_per_MWh": round2(lmp_map[bus])}
                for bus in sorted(lmp_map)
            ],
            "binding_lines": binding_lines,
        }

    pre_event = solve_case("pre_event", {})
    emergency_overrides = {
        (int(item["from_bus"]), int(item["to_bus"])): float(item["derated_limit_MW"])
        for item in event["emergency_deratings"]
    }
    emergency_case = solve_case("emergency_case", emergency_overrides)

    pre_lmp = {item["bus"]: item["lmp_dollars_per_MWh"] for item in pre_event["lmp_by_bus"]}
    emergency_lmp = {item["bus"]: item["lmp_dollars_per_MWh"] for item in emergency_case["lmp_by_bus"]}

    def classify_risk(increase):
        if increase >= float(event["severe_price_increase_threshold"]):
            return "severe"
        if increase >= float(event["elevated_price_increase_threshold"]):
            return "elevated"
        return "watch"

    load_center_price_spikes = []
    for bus in event["monitored_load_centers"]:
        increase = emergency_lmp[bus] - pre_lmp[bus]
        load_center_price_spikes.append(
            {
                "bus": int(bus),
                "pre_event_lmp": round2(pre_lmp[bus]),
                "emergency_lmp": round2(emergency_lmp[bus]),
                "increase_dollars_per_MWh": round2(increase),
                "risk_tier": classify_risk(increase),
            }
        )
    load_center_price_spikes.sort(key=lambda item: (-item["increase_dollars_per_MWh"], item["bus"]))

    pre_binding = {(item["from"], item["to"]) for item in pre_event["binding_lines"]}
    emergency_binding_map = {(item["from"], item["to"]): item for item in emergency_case["binding_lines"]}
    newly_binding_derated_lines = []
    for item in event["emergency_deratings"]:
        key = (int(item["from_bus"]), int(item["to_bus"]))
        if key not in pre_binding and key in emergency_binding_map:
            newly_binding_derated_lines.append(
                {
                    "from": key[0],
                    "to": key[1],
                    "base_limit_MW": round2(branch_limits[key]),
                    "emergency_limit_MW": round2(float(item["derated_limit_MW"])),
                    "emergency_flow_MW": round2(emergency_binding_map[key]["flow_MW"]),
                }
            )
    newly_binding_derated_lines.sort(key=lambda item: (item["from"], item["to"]))

    island_buses = [int(bus) for bus in event["island_buses"]]
    average_island_lmp = sum(emergency_lmp[bus] for bus in island_buses) / len(island_buses)
    reference_bus = int(event["reference_bus"])

    return {
        "pre_event": pre_event,
        "emergency_case": emergency_case,
        "risk_summary": {
            "production_cost_increase_dollars_per_hour": round2(
                emergency_case["total_cost_dollars_per_hour"] - pre_event["total_cost_dollars_per_hour"]
            ),
            "monitored_load_center_price_spikes": load_center_price_spikes,
            "newly_binding_derated_lines": newly_binding_derated_lines,
            "price_island_summary": {
                "reference_bus": reference_bus,
                "island_buses": island_buses,
                "island_load_MW": round2(sum(bus_load[bus] for bus in island_buses)),
                "average_emergency_lmp_dollars_per_MWh": round2(average_island_lmp),
                "premium_vs_reference_bus_dollars_per_MWh": round2(
                    average_island_lmp - emergency_lmp[reference_bus]
                ),
            },
        },
    }


class TestSchema:
    def test_top_level_keys(self, output):
        assert set(output) == {"pre_event", "emergency_case", "risk_summary"}

    def test_scenario_sections(self, output, network):
        expected_buses = sorted(int(row[0]) for row in network["bus"])
        for section in ["pre_event", "emergency_case"]:
            case = output[section]
            assert case["scenario_id"] == section
            assert isinstance(case["binding_lines"], list)
            assert [item["bus"] for item in case["lmp_by_bus"]] == expected_buses

    def test_risk_summary_shape(self, output, event):
        summary = output["risk_summary"]
        assert "production_cost_increase_dollars_per_hour" in summary
        assert "monitored_load_center_price_spikes" in summary
        assert "newly_binding_derated_lines" in summary
        assert "price_island_summary" in summary
        assert len(summary["monitored_load_center_price_spikes"]) == len(event["monitored_load_centers"])


class TestValues:
    def test_exact_output(self, output, reference):
        assert output == reference

    def test_emergency_cost_higher(self, output):
        assert (
            output["emergency_case"]["total_cost_dollars_per_hour"]
            > output["pre_event"]["total_cost_dollars_per_hour"]
        )

    def test_price_island_premium_positive(self, output):
        assert output["risk_summary"]["price_island_summary"]["premium_vs_reference_bus_dollars_per_MWh"] > 0
