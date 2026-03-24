#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from collections import defaultdict
from pathlib import Path


def r4(value):
    return round(float(value), 4)


def positive(value):
    value = float(value)
    return value if value > 0 else 0.0


def normalize_high(value, min_value, max_value):
    if abs(max_value - min_value) < 1e-12:
        return 1.0
    return (value - min_value) / (max_value - min_value)


def normalize_low(value, min_value, max_value):
    if abs(max_value - min_value) < 1e-12:
        return 1.0
    return (max_value - value) / (max_value - min_value)


def resolve_input(env_name, root_name):
    override = os.environ.get(env_name)
    if override:
        return Path(override)
    root_path = Path("/root") / root_name
    try:
        root_exists = root_path.exists()
    except PermissionError:
        root_exists = False
    if root_exists:
        return root_path
    return Path.cwd() / "environment" / root_name


def resolve_output():
    override = os.environ.get("REPORT_OUTPUT")
    if override:
        return Path(override)
    root_path = Path("/root/ev_depot_screen.json")
    try:
        root_parent_writable = root_path.parent.exists() and os.access(root_path.parent, os.W_OK)
    except PermissionError:
        root_parent_writable = False
    if root_parent_writable:
        return root_path
    return Path.cwd() / "ev_depot_screen.json"


with resolve_input("NETWORK_FILE", "network.json").open(encoding="utf-8") as handle:
    network = json.load(handle)
with resolve_input("CANDIDATE_FILE", "candidate_buses.json").open(encoding="utf-8") as handle:
    config = json.load(handle)

bus_rows = network["bus"]
gen_rows = network["gen"]
branch_rows = network["branch"]

bus_by_id = {int(row[0]): row for row in bus_rows}
gen_rows_by_bus = defaultdict(list)
for row in gen_rows:
    gen_rows_by_bus[int(row[0])].append(row)

active_branch_rows_by_bus = defaultdict(list)
neighbor_buses_by_bus = defaultdict(set)
for row in branch_rows:
    if int(row[10]) != 1:
        continue
    from_bus = int(row[0])
    to_bus = int(row[1])
    active_branch_rows_by_bus[from_bus].append(row)
    active_branch_rows_by_bus[to_bus].append(row)
    neighbor_buses_by_bus[from_bus].add(to_bus)
    neighbor_buses_by_bus[to_bus].add(from_bus)

preferred_voltage_kv = float(config["preferred_voltage_kV"])
strong_branch_capacity_threshold = float(config["strong_branch_capacity_threshold_MVA"])
weights = config["weights"]

records = []
for item in config["candidate_buses"]:
    bus_id = int(item["bus"])
    row = bus_by_id[bus_id]
    branch_rows_at_bus = active_branch_rows_by_bus[bus_id]
    unique_neighbors = sorted(neighbor_buses_by_bus[bus_id])

    same_bus_generation_margin = sum(
        max(float(gen_row[8]) - float(gen_row[1]), 0.0)
        for gen_row in gen_rows_by_bus.get(bus_id, [])
        if int(gen_row[7]) == 1
    )
    adjacent_branch_capacity_sum = sum(max(float(branch_row[5]), 0.0) for branch_row in branch_rows_at_bus)
    max_adjacent_branch = max((max(float(branch_row[5]), 0.0) for branch_row in branch_rows_at_bus), default=0.0)
    one_hop_115_plus = sum(
        1 for neighbor_bus in unique_neighbors if float(bus_by_id[neighbor_bus][9]) >= preferred_voltage_kv
    )
    one_hop_generator_bus_count = sum(
        1
        for neighbor_bus in unique_neighbors
        if any(
            int(gen_row[7]) == 1 and (float(gen_row[8]) - float(gen_row[1])) > 0.0
            for gen_row in gen_rows_by_bus.get(neighbor_bus, [])
        )
    )
    one_hop_total_neighbor_load = sum(positive(bus_by_id[neighbor_bus][2]) for neighbor_bus in unique_neighbors)

    records.append(
        {
            "bus": bus_id,
            "site_code": item["site_code"],
            "base_kV": float(row[9]),
            "existing_load_MW": positive(row[2]),
            "same_bus_generation_margin_MW": same_bus_generation_margin,
            "adjacent_branch_count": len(branch_rows_at_bus),
            "adjacent_branch_capacity_MVA_sum": adjacent_branch_capacity_sum,
            "max_adjacent_branch_MVA": max_adjacent_branch,
            "one_hop_neighbor_count": len(unique_neighbors),
            "one_hop_115kV_plus_neighbor_count": one_hop_115_plus,
            "one_hop_generator_bus_count": one_hop_generator_bus_count,
            "one_hop_total_neighbor_load_MW": one_hop_total_neighbor_load,
        }
    )


def bounds(key):
    values = [record[key] for record in records]
    return min(values), max(values)


base_kv_min, base_kv_max = bounds("base_kV")
load_min, load_max = bounds("existing_load_MW")
margin_min, margin_max = bounds("same_bus_generation_margin_MW")
capacity_min, capacity_max = bounds("adjacent_branch_capacity_MVA_sum")
neighbor_count_min, neighbor_count_max = bounds("one_hop_neighbor_count")
hv_neighbor_min, hv_neighbor_max = bounds("one_hop_115kV_plus_neighbor_count")
gen_neighbor_min, gen_neighbor_max = bounds("one_hop_generator_bus_count")

ranked = []
for record in records:
    voltage_level = normalize_high(record["base_kV"], base_kv_min, base_kv_max)
    existing_load = normalize_low(record["existing_load_MW"], load_min, load_max)
    same_bus_generation_margin = normalize_high(
        record["same_bus_generation_margin_MW"], margin_min, margin_max
    )
    adjacent_branch_capacity = normalize_high(
        record["adjacent_branch_capacity_MVA_sum"], capacity_min, capacity_max
    )
    one_hop_topology = (
        0.5 * normalize_high(record["one_hop_neighbor_count"], neighbor_count_min, neighbor_count_max)
        + 0.3
        * normalize_high(
            record["one_hop_115kV_plus_neighbor_count"], hv_neighbor_min, hv_neighbor_max
        )
        + 0.2
        * normalize_high(record["one_hop_generator_bus_count"], gen_neighbor_min, gen_neighbor_max)
    )
    score = 100.0 * (
        float(weights["voltage_level"]) * voltage_level
        + float(weights["existing_load"]) * existing_load
        + float(weights["same_bus_generation_margin"]) * same_bus_generation_margin
        + float(weights["adjacent_branch_capacity"]) * adjacent_branch_capacity
        + float(weights["one_hop_topology"]) * one_hop_topology
    )

    base_kv = record["base_kV"]
    if (
        base_kv >= float(config["preferred_voltage_kV"])
        and score >= float(config["status_thresholds"]["preferred_min_score"])
    ):
        status = "preferred"
    elif (
        base_kv >= float(config["minimum_voltage_kV"])
        and score >= float(config["status_thresholds"]["conditional_min_score"])
    ):
        status = "conditional"
    else:
        status = "reject"

    ranked.append(
        {
            "bus": record["bus"],
            "site_code": record["site_code"],
            "score": r4(score),
            "status": status,
            "score_breakdown": {
                "voltage_level": r4(voltage_level),
                "existing_load": r4(existing_load),
                "same_bus_generation_margin": r4(same_bus_generation_margin),
                "adjacent_branch_capacity": r4(adjacent_branch_capacity),
                "one_hop_topology": r4(one_hop_topology),
            },
            "screening_flags": {
                "meets_minimum_voltage": base_kv >= float(config["minimum_voltage_kV"]),
                "meets_preferred_voltage": base_kv >= float(config["preferred_voltage_kV"]),
                "has_same_bus_generation_margin": record["same_bus_generation_margin_MW"] > 0.0,
                "strong_branch_capacity_proxy": (
                    record["adjacent_branch_capacity_MVA_sum"] >= strong_branch_capacity_threshold
                ),
            },
            "summary": {
                "base_kV": r4(record["base_kV"]),
                "existing_load_MW": r4(record["existing_load_MW"]),
                "same_bus_generation_margin_MW": r4(record["same_bus_generation_margin_MW"]),
                "adjacent_branch_count": int(record["adjacent_branch_count"]),
                "adjacent_branch_capacity_MVA_sum": r4(record["adjacent_branch_capacity_MVA_sum"]),
                "max_adjacent_branch_MVA": r4(record["max_adjacent_branch_MVA"]),
                "one_hop_neighbor_count": int(record["one_hop_neighbor_count"]),
                "one_hop_115kV_plus_neighbor_count": int(record["one_hop_115kV_plus_neighbor_count"]),
                "one_hop_generator_bus_count": int(record["one_hop_generator_bus_count"]),
                "one_hop_total_neighbor_load_MW": r4(record["one_hop_total_neighbor_load_MW"]),
            },
        }
    )

ranked.sort(
    key=lambda item: (
        -item["score"],
        -item["summary"]["adjacent_branch_capacity_MVA_sum"],
        item["bus"],
    )
)

for index, item in enumerate(ranked, start=1):
    item["rank"] = index

preferred_bus_ids = [item["bus"] for item in ranked if item["status"] == "preferred"]

output = {
    "screening_context": {
        "depot_name": config["depot_name"],
        "depot_peak_demand_MW": r4(config["depot_peak_demand_MW"]),
        "minimum_voltage_kV": r4(config["minimum_voltage_kV"]),
        "preferred_voltage_kV": r4(config["preferred_voltage_kV"]),
        "strong_branch_capacity_threshold_MVA": r4(config["strong_branch_capacity_threshold_MVA"]),
        "candidate_count": len(config["candidate_buses"]),
    },
    "status_summary": {
        "preferred_count": sum(1 for item in ranked if item["status"] == "preferred"),
        "conditional_count": sum(1 for item in ranked if item["status"] == "conditional"),
        "reject_count": sum(1 for item in ranked if item["status"] == "reject"),
        "recommended_bus_ids": preferred_bus_ids,
    },
    "ranked_candidates": ranked,
}

with resolve_output().open("w", encoding="utf-8") as handle:
    json.dump(output, handle, indent=2)
    handle.write("\n")
PY
