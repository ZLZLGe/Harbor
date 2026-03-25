#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
import heapq

INPUT_FILE = "/root/balancing_area_portfolio.json"
OUTPUT_FILE = "/root/balancing_dispatch_report.json"
EPS = 1e-9


class MinCostFlow:
    def __init__(self, n):
        self.graph = [[] for _ in range(n)]

    def add_edge(self, src, dst, capacity, cost):
        forward = {"to": dst, "rev": len(self.graph[dst]), "cap": float(capacity), "cost": float(cost)}
        reverse = {"to": src, "rev": len(self.graph[src]), "cap": 0.0, "cost": -float(cost)}
        self.graph[src].append(forward)
        self.graph[dst].append(reverse)
        return len(self.graph[src]) - 1

    def min_cost_flow(self, src, dst, required_flow):
        node_count = len(self.graph)
        potentials = [0.0] * node_count
        total_flow = 0.0
        total_cost = 0.0

        while total_flow + EPS < required_flow:
            dist = [math.inf] * node_count
            prev = [None] * node_count
            dist[src] = 0.0
            heap = [(0.0, src)]

            while heap:
                curr_dist, node = heapq.heappop(heap)
                if curr_dist > dist[node] + EPS:
                    continue
                for edge_index, edge in enumerate(self.graph[node]):
                    if edge["cap"] <= EPS:
                        continue
                    next_node = edge["to"]
                    next_dist = curr_dist + edge["cost"] + potentials[node] - potentials[next_node]
                    if next_dist + EPS < dist[next_node]:
                        dist[next_node] = next_dist
                        prev[next_node] = (node, edge_index)
                        heapq.heappush(heap, (next_dist, next_node))

            if math.isinf(dist[dst]):
                raise RuntimeError("Dispatch problem is infeasible")

            for node, value in enumerate(dist):
                if value < math.inf:
                    potentials[node] += value

            push = required_flow - total_flow
            node = dst
            while node != src:
                prev_node, edge_index = prev[node]
                push = min(push, self.graph[prev_node][edge_index]["cap"])
                node = prev_node

            node = dst
            while node != src:
                prev_node, edge_index = prev[node]
                edge = self.graph[prev_node][edge_index]
                reverse = self.graph[node][edge["rev"]]
                edge["cap"] -= push
                reverse["cap"] += push
                total_cost += push * edge["cost"]
                node = prev_node

            total_flow += push

        return total_cost


with open(INPUT_FILE, encoding="utf-8") as f:
    portfolio = json.load(f)

units = portfolio["units"]
base_energy = sum(unit["p_min_MW"] for unit in units)
remaining_energy = portfolio["load_MW"] - base_energy
reserve_requirement = portfolio["reserve_requirement_MW"]

if remaining_energy < -EPS:
    raise RuntimeError("Load is below the aggregate minimum generation level")

node_source = 0
unit_offset = 1
node_energy = unit_offset + len(units)
node_reserve = node_energy + 1
node_sink = node_reserve + 1

flow = MinCostFlow(node_sink + 1)
energy_edge_refs = []
reserve_edge_refs = []

for idx, unit in enumerate(units):
    headroom = unit["p_max_MW"] - unit["p_min_MW"]
    reserve_cap = min(headroom, unit["reserve_offer_cap_MW"])
    unit_node = unit_offset + idx

    flow.add_edge(node_source, unit_node, headroom, 0.0)
    energy_edge_refs.append((unit_node, flow.add_edge(
        unit_node,
        node_energy,
        headroom,
        unit["energy_offer_dollars_per_MWh"],
    )))
    reserve_edge_refs.append((unit_node, flow.add_edge(
        unit_node,
        node_reserve,
        reserve_cap,
        unit["reserve_offer_dollars_per_MW"],
    )))

flow.add_edge(node_energy, node_sink, remaining_energy, 0.0)
flow.add_edge(node_reserve, node_sink, reserve_requirement, 0.0)

variable_cost = flow.min_cost_flow(node_source, node_sink, remaining_energy + reserve_requirement)

base_cost = sum(unit["p_min_MW"] * unit["energy_offer_dollars_per_MWh"] for unit in units)
total_cost = base_cost + variable_cost

generator_dispatch = []
for unit, (energy_node, energy_edge_index), (_, reserve_edge_index) in zip(units, energy_edge_refs, reserve_edge_refs):
    energy_edge = flow.graph[energy_node][energy_edge_index]
    reserve_edge = flow.graph[energy_node][reserve_edge_index]
    used_energy = flow.graph[node_energy][energy_edge["rev"]]["cap"]
    used_reserve = flow.graph[node_reserve][reserve_edge["rev"]]["cap"]
    energy = unit["p_min_MW"] + used_energy
    reserve = used_reserve
    unused_headroom = unit["p_max_MW"] - energy - reserve

    generator_dispatch.append({
        "unit_id": unit["unit_id"],
        "fuel": unit["fuel"],
        "energy_MW": round(energy, 2),
        "reserve_MW": round(reserve, 2),
        "unused_headroom_MW": round(unused_headroom, 2),
    })

total_energy = sum(entry["energy_MW"] for entry in generator_dispatch)
total_reserve = sum(entry["reserve_MW"] for entry in generator_dispatch)
total_margin = sum(entry["unused_headroom_MW"] for entry in generator_dispatch)

report = {
    "balancing_area": portfolio["balancing_area"],
    "interval_start": portfolio["interval_start"],
    "generator_dispatch": generator_dispatch,
    "totals": {
        "load_MW": round(portfolio["load_MW"], 2),
        "energy_MW": round(total_energy, 2),
        "reserve_requirement_MW": round(reserve_requirement, 2),
        "reserve_MW": round(total_reserve, 2),
        "total_cost_dollars_per_hour": round(total_cost, 2),
        "uncommitted_margin_MW": round(total_margin, 2),
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
