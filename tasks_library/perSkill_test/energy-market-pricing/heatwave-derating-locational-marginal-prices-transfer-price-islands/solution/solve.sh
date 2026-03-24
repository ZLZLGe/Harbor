#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json

NETWORK_FILE = "/root/compact_heatwave_network.json"
EVENT_FILE = "/root/heatwave_event.json"
OUTPUT_FILE = "/root/price_island_risk.json"


def round2(value):
    return round(float(value) + 1e-9, 2)


with open(NETWORK_FILE, encoding="utf-8") as f:
    network = json.load(f)

with open(EVENT_FILE, encoding="utf-8") as f:
    event = json.load(f)

bus_load = {int(row[0]): float(row[2]) for row in network["bus"]}
gen_by_bus = {int(row[0]): row for row in network["gen"]}
cost_by_bus = {
    int(network["gen"][idx][0]): float(network["gencost"][idx][5])
    for idx in range(len(network["gen"]))
}
reserve_requirement = float(network["reserve_requirement"])
reserve_capacity = {
    int(network["gen"][idx][0]): float(network["reserve_capacity"][idx])
    for idx in range(len(network["gen"]))
}
branch_limits = {
    (int(row[0]), int(row[1])): float(row[5])
    for row in network["branch"]
}


def get_limit(from_bus, to_bus, overrides):
    if (from_bus, to_bus) in overrides:
        return overrides[(from_bus, to_bus)]
    if (to_bus, from_bus) in overrides:
        return overrides[(to_bus, from_bus)]
    if (from_bus, to_bus) in branch_limits:
        return branch_limits[(from_bus, to_bus)]
    return branch_limits[(to_bus, from_bus)]


def scenario_results(scenario_id, overrides):
    limit_629_64 = get_limit(629, 64, overrides)
    limit_64_1501 = get_limit(64, 1501, overrides)

    load_672 = bus_load[672]
    load_629 = bus_load[629]
    load_64 = bus_load[64]
    load_1501 = bus_load[1501]

    gen1_bus, gen2_bus, gen3_bus, gen4_bus = 2615, 672, 64, 1501
    pmax1 = float(gen_by_bus[gen1_bus][8])
    pmax2 = float(gen_by_bus[gen2_bus][8])
    pmax3 = float(gen_by_bus[gen3_bus][8])
    pmax4 = float(gen_by_bus[gen4_bus][8])

    local_1501 = max(0.0, load_1501 - limit_64_1501)
    local_64 = max(0.0, load_64 + load_1501 - local_1501 - limit_629_64)
    import_to_1501 = load_1501 - local_1501
    import_to_64_pocket = load_64 + import_to_1501 - local_64
    upstream_need = load_672 + load_629 + import_to_64_pocket

    g1 = min(pmax1, upstream_need)
    g2 = upstream_need - g1
    g3 = local_64
    g4 = local_1501

    assert g2 <= pmax2 + 1e-9, "Scenario needs more mid-merit generation than available"
    assert g3 <= pmax3 + 1e-9, "Scenario needs more local peaker output than available"
    assert g4 <= pmax4 + 1e-9, "Scenario needs more emergency generation than available"

    reserve_headroom = (
        min(reserve_capacity[gen1_bus], pmax1 - g1)
        + min(reserve_capacity[gen2_bus], pmax2 - g2)
        + min(reserve_capacity[gen3_bus], pmax3 - g3)
        + min(reserve_capacity[gen4_bus], pmax4 - g4)
    )
    reserve_mcp = 0.0 if reserve_headroom + 1e-9 >= reserve_requirement else None
    if reserve_mcp is None:
        raise ValueError("Reserve requirement is not feasible in this scenario")

    left_lmp = cost_by_bus[gen2_bus] if g2 > 1e-9 else cost_by_bus[gen1_bus]
    bus64_lmp = cost_by_bus[gen3_bus] if g3 > 1e-9 else left_lmp
    bus1501_lmp = cost_by_bus[gen4_bus] if g4 > 1e-9 else bus64_lmp

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
        (672, 629): load_629 + import_to_64_pocket,
        (629, 64): import_to_64_pocket,
        (64, 1501): import_to_1501,
    }

    binding_lines = []
    threshold = float(event["binding_threshold_pct"])
    for row in network["branch"]:
        from_bus = int(row[0])
        to_bus = int(row[1])
        limit = get_limit(from_bus, to_bus, overrides)
        flow = flows[(from_bus, to_bus)]
        loading_pct = abs(flow) / limit * 100.0
        if loading_pct + 1e-9 >= threshold:
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
        g1 * cost_by_bus[gen1_bus]
        + g2 * cost_by_bus[gen2_bus]
        + g3 * cost_by_bus[gen3_bus]
        + g4 * cost_by_bus[gen4_bus]
    )

    return {
        "scenario_id": scenario_id,
        "dispatch": {2615: g1, 672: g2, 64: g3, 1501: g4},
        "flows": flows,
        "total_cost_dollars_per_hour": round2(total_cost),
        "reserve_mcp_dollars_per_MWh": round2(reserve_mcp),
        "lmp_by_bus": [
            {"bus": bus, "lmp_dollars_per_MWh": round2(lmp_map[bus])}
            for bus in sorted(lmp_map)
        ],
        "binding_lines": binding_lines,
    }


pre_event = scenario_results("pre_event", {})
emergency_overrides = {
    (int(item["from_bus"]), int(item["to_bus"])): float(item["derated_limit_MW"])
    for item in event["emergency_deratings"]
}
emergency_case = scenario_results("emergency_case", emergency_overrides)

pre_lmp = {item["bus"]: item["lmp_dollars_per_MWh"] for item in pre_event["lmp_by_bus"]}
em_lmp = {item["bus"]: item["lmp_dollars_per_MWh"] for item in emergency_case["lmp_by_bus"]}


def classify_risk(increase):
    if increase >= float(event["severe_price_increase_threshold"]):
        return "severe"
    if increase >= float(event["elevated_price_increase_threshold"]):
        return "elevated"
    return "watch"


price_spikes = []
for bus in event["monitored_load_centers"]:
    increase = em_lmp[bus] - pre_lmp[bus]
    price_spikes.append(
        {
            "bus": int(bus),
            "pre_event_lmp": round2(pre_lmp[bus]),
            "emergency_lmp": round2(em_lmp[bus]),
            "increase_dollars_per_MWh": round2(increase),
            "risk_tier": classify_risk(increase),
        }
    )
price_spikes.sort(key=lambda item: (-item["increase_dollars_per_MWh"], item["bus"]))

pre_binding = {(item["from"], item["to"]) for item in pre_event["binding_lines"]}
em_binding_map = {(item["from"], item["to"]): item for item in emergency_case["binding_lines"]}
newly_binding = []
for item in event["emergency_deratings"]:
    key = (int(item["from_bus"]), int(item["to_bus"]))
    if key not in pre_binding and key in em_binding_map:
        newly_binding.append(
            {
                "from": key[0],
                "to": key[1],
                "base_limit_MW": round2(branch_limits[key]),
                "emergency_limit_MW": round2(float(item["derated_limit_MW"])),
                "emergency_flow_MW": round2(em_binding_map[key]["flow_MW"]),
            }
        )
newly_binding.sort(key=lambda item: (item["from"], item["to"]))

island_buses = [int(bus) for bus in event["island_buses"]]
reference_bus = int(event["reference_bus"])
average_island_lmp = sum(em_lmp[bus] for bus in island_buses) / len(island_buses)
reference_lmp = em_lmp[reference_bus]
island_load = sum(bus_load[bus] for bus in island_buses)

output = {
    "pre_event": {
        "scenario_id": pre_event["scenario_id"],
        "total_cost_dollars_per_hour": pre_event["total_cost_dollars_per_hour"],
        "reserve_mcp_dollars_per_MWh": pre_event["reserve_mcp_dollars_per_MWh"],
        "lmp_by_bus": pre_event["lmp_by_bus"],
        "binding_lines": pre_event["binding_lines"],
    },
    "emergency_case": {
        "scenario_id": emergency_case["scenario_id"],
        "total_cost_dollars_per_hour": emergency_case["total_cost_dollars_per_hour"],
        "reserve_mcp_dollars_per_MWh": emergency_case["reserve_mcp_dollars_per_MWh"],
        "lmp_by_bus": emergency_case["lmp_by_bus"],
        "binding_lines": emergency_case["binding_lines"],
    },
    "risk_summary": {
        "production_cost_increase_dollars_per_hour": round2(
            emergency_case["total_cost_dollars_per_hour"] - pre_event["total_cost_dollars_per_hour"]
        ),
        "monitored_load_center_price_spikes": price_spikes,
        "newly_binding_derated_lines": newly_binding,
        "price_island_summary": {
            "reference_bus": reference_bus,
            "island_buses": island_buses,
            "island_load_MW": round2(island_load),
            "average_emergency_lmp_dollars_per_MWh": round2(average_island_lmp),
            "premium_vs_reference_bus_dollars_per_MWh": round2(average_island_lmp - reference_lmp),
        },
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
    f.write("\n")
PY
