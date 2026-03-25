#!/bin/bash
set -euo pipefail

NETWORK_FILE="${NETWORK_FILE:-network.json}"
CANDIDATE_FILE="${CANDIDATE_FILE:-candidate_sites.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-battery_site_ranking.csv}"
export NETWORK_FILE CANDIDATE_FILE OUTPUT_FILE

python3 <<'PY'
import csv
import json
import os
from collections import defaultdict

NETWORK_FILE = os.environ["NETWORK_FILE"]
CANDIDATE_FILE = os.environ["CANDIDATE_FILE"]
OUTPUT_FILE = os.environ["OUTPUT_FILE"]

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


with open(NETWORK_FILE, encoding="utf-8") as f:
    network = json.load(f)

with open(CANDIDATE_FILE, encoding="utf-8", newline="") as f:
    candidates = list(csv.DictReader(f))

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

with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)
PY
