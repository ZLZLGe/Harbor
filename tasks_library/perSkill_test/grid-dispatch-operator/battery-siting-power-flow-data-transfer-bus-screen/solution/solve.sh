#!/bin/bash
set -euo pipefail

NETWORK_FILE="${NETWORK_FILE:-/root/interconnection_network.json}"
CANDIDATE_FILE="${CANDIDATE_FILE:-/root/candidate_buses.json}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/interconnection_screen.json}"
export NETWORK_FILE CANDIDATE_FILE OUTPUT_FILE

python3 <<'PY'
import json
import os
from collections import defaultdict


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


network_file = os.environ["NETWORK_FILE"]
candidate_file = os.environ["CANDIDATE_FILE"]
output_file = os.environ["OUTPUT_FILE"]

with open(network_file, encoding="utf-8") as f:
    network = json.load(f)

with open(candidate_file, encoding="utf-8") as f:
    study = json.load(f)

buses = network["bus"]
gens = network["gen"]
branches = network["branch"]
thresholds = study["voltage_class_thresholds_kV"]
ehv_min = float(thresholds["ehv_min"])
hv_min = float(thresholds["hv_min"])

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
    pg = float(row[1])
    pmax = float(row[8])
    generation_headroom_by_bus[bus] += max(pmax - pg, 0.0)


def classify_voltage(voltage_kv):
    if voltage_kv >= ehv_min:
        return "EHV", 3
    if voltage_kv >= hv_min:
        return "HV", 2
    return "Subtransmission", 1


ranked_rows = []
for bus in study["candidate_buses"]:
    bus_num = int(bus)
    voltage_kv = bus_voltage[bus_num]
    voltage_class, voltage_rank = classify_voltage(voltage_kv)
    neighborhood = {bus_num, *adjacency[bus_num]}

    nearby_load = sum(positive_load.get(neighbor, 0.0) for neighbor in neighborhood)
    local_headroom = sum(generation_headroom_by_bus.get(neighbor, 0.0) for neighbor in neighborhood)

    ranked_rows.append(
        {
            "bus": bus_num,
            "voltage_kV": round2(voltage_kv),
            "voltage_class": voltage_class,
            "voltage_class_rank": voltage_rank,
            "connected_in_service_branches": connected_branch_count[bus_num],
            "connected_branch_transfer_MW": round2(transfer_capability[bus_num]),
            "nearby_load_sink_MW": round2(nearby_load),
            "local_generation_headroom_MW": round2(local_headroom),
        }
    )

ranked_rows.sort(
    key=lambda row: (
        -row["voltage_class_rank"],
        -row["connected_branch_transfer_MW"],
        -row["nearby_load_sink_MW"],
        -row["local_generation_headroom_MW"],
        row["bus"],
    )
)

for index, row in enumerate(ranked_rows, start=1):
    row["rank"] = index

output = {
    "project_name": study["project_name"],
    "candidate_count": len(ranked_rows),
    "ranking_rule": {
        "primary": "voltage_class_rank_desc",
        "secondary": "connected_branch_transfer_MW_desc",
        "tertiary": "nearby_load_sink_MW_desc",
        "quaternary": "local_generation_headroom_MW_desc",
        "tie_breaker": "bus_asc",
    },
    "ranked_buses": ranked_rows,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
PY
