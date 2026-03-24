#!/bin/bash
set -e

python3 <<'PY'
import json


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


with open("/root/qc_network.json", encoding="utf-8") as f:
    network = json.load(f)

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
    if reactance == 0.0:
        zero_reactance.append(
            {
                "branch_row_id": row_id,
                "from": norm_from,
                "to": norm_to,
                "reactance_pu": round2(reactance),
                "rate_a_MVA": round2(rate_a),
            }
        )
    if rate_a <= 0.0:
        zero_rating.append(
            {
                "branch_row_id": row_id,
                "from": norm_from,
                "to": norm_to,
                "reactance_pu": round2(reactance),
                "rate_a_MVA": round2(rate_a),
            }
        )

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

report = {
    "snapshot_name": network.get("name", "unknown_snapshot"),
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

with open("/root/topology_audit.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
