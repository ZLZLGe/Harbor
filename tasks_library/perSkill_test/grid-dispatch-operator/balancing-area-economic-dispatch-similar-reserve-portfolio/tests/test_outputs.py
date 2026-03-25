import json
import math
import heapq
import os

import pytest

INPUT_FILE = "/root/balancing_area_portfolio.json"
OUTPUT_FILE = "/root/balancing_dispatch_report.json"
EPS = 1e-6


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


def solve_reference(portfolio):
    units = portfolio["units"]
    base_energy = sum(unit["p_min_MW"] for unit in units)
    remaining_energy = portfolio["load_MW"] - base_energy
    reserve_requirement = portfolio["reserve_requirement_MW"]

    node_source = 0
    unit_offset = 1
    node_energy = unit_offset + len(units)
    node_reserve = node_energy + 1
    node_sink = node_reserve + 1

    flow = MinCostFlow(node_sink + 1)
    energy_refs = []
    reserve_refs = []

    for idx, unit in enumerate(units):
        headroom = unit["p_max_MW"] - unit["p_min_MW"]
        reserve_cap = min(headroom, unit["reserve_offer_cap_MW"])
        unit_node = unit_offset + idx
        flow.add_edge(node_source, unit_node, headroom, 0.0)
        energy_refs.append((unit_node, flow.add_edge(
            unit_node,
            node_energy,
            headroom,
            unit["energy_offer_dollars_per_MWh"],
        )))
        reserve_refs.append((unit_node, flow.add_edge(
            unit_node,
            node_reserve,
            reserve_cap,
            unit["reserve_offer_dollars_per_MW"],
        )))

    flow.add_edge(node_energy, node_sink, remaining_energy, 0.0)
    flow.add_edge(node_reserve, node_sink, reserve_requirement, 0.0)
    variable_cost = flow.min_cost_flow(node_source, node_sink, remaining_energy + reserve_requirement)
    base_cost = sum(unit["p_min_MW"] * unit["energy_offer_dollars_per_MWh"] for unit in units)

    dispatch = {}
    for unit, (unit_node, energy_edge_index), (_, reserve_edge_index) in zip(units, energy_refs, reserve_refs):
        energy_edge = flow.graph[unit_node][energy_edge_index]
        reserve_edge = flow.graph[unit_node][reserve_edge_index]
        used_energy = flow.graph[node_energy][energy_edge["rev"]]["cap"]
        used_reserve = flow.graph[node_reserve][reserve_edge["rev"]]["cap"]
        energy = unit["p_min_MW"] + used_energy
        reserve = used_reserve
        dispatch[unit["unit_id"]] = {
            "energy_MW": energy,
            "reserve_MW": reserve,
            "unused_headroom_MW": unit["p_max_MW"] - energy - reserve,
        }

    return {
        "total_cost_dollars_per_hour": base_cost + variable_cost,
        "dispatch": dispatch,
    }


@pytest.fixture(scope="module")
def portfolio():
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference(portfolio):
    return solve_reference(portfolio)


def test_schema(report, portfolio):
    assert report["balancing_area"] == portfolio["balancing_area"]
    assert report["interval_start"] == portfolio["interval_start"]
    assert isinstance(report["generator_dispatch"], list)
    assert len(report["generator_dispatch"]) == len(portfolio["units"])
    assert "totals" in report

    expected_fields = {"unit_id", "fuel", "energy_MW", "reserve_MW", "unused_headroom_MW"}
    for entry in report["generator_dispatch"]:
        assert expected_fields.issubset(entry.keys())

    totals_fields = {
        "load_MW",
        "energy_MW",
        "reserve_requirement_MW",
        "reserve_MW",
        "total_cost_dollars_per_hour",
        "uncommitted_margin_MW",
    }
    assert totals_fields.issubset(report["totals"].keys())


def test_dispatch_order_matches_input(report, portfolio):
    reported_ids = [entry["unit_id"] for entry in report["generator_dispatch"]]
    expected_ids = [unit["unit_id"] for unit in portfolio["units"]]
    assert reported_ids == expected_ids


def test_feasibility_and_totals(report, portfolio):
    unit_map = {unit["unit_id"]: unit for unit in portfolio["units"]}

    total_energy = 0.0
    total_reserve = 0.0
    total_margin = 0.0

    for entry in report["generator_dispatch"]:
        unit = unit_map[entry["unit_id"]]
        energy = entry["energy_MW"]
        reserve = entry["reserve_MW"]
        margin = entry["unused_headroom_MW"]

        assert entry["fuel"] == unit["fuel"]
        assert unit["p_min_MW"] - EPS <= energy <= unit["p_max_MW"] + EPS
        assert -EPS <= reserve <= unit["reserve_offer_cap_MW"] + EPS
        assert energy + reserve <= unit["p_max_MW"] + EPS
        assert margin == pytest.approx(unit["p_max_MW"] - energy - reserve, abs=1e-2)

        total_energy += energy
        total_reserve += reserve
        total_margin += margin

    totals = report["totals"]
    assert total_energy == pytest.approx(portfolio["load_MW"], abs=1e-2)
    assert total_reserve == pytest.approx(portfolio["reserve_requirement_MW"], abs=1e-2)
    assert totals["load_MW"] == pytest.approx(portfolio["load_MW"], abs=1e-2)
    assert totals["energy_MW"] == pytest.approx(total_energy, abs=1e-2)
    assert totals["reserve_requirement_MW"] == pytest.approx(portfolio["reserve_requirement_MW"], abs=1e-2)
    assert totals["reserve_MW"] == pytest.approx(total_reserve, abs=1e-2)
    assert totals["uncommitted_margin_MW"] == pytest.approx(total_margin, abs=1e-2)


def test_reported_cost_is_consistent(report, portfolio):
    unit_map = {unit["unit_id"]: unit for unit in portfolio["units"]}
    calculated_cost = 0.0
    for entry in report["generator_dispatch"]:
        unit = unit_map[entry["unit_id"]]
        calculated_cost += entry["energy_MW"] * unit["energy_offer_dollars_per_MWh"]
        calculated_cost += entry["reserve_MW"] * unit["reserve_offer_dollars_per_MW"]

    assert report["totals"]["total_cost_dollars_per_hour"] == pytest.approx(calculated_cost, abs=1e-2)


def test_total_cost_is_optimal(report, reference):
    assert report["totals"]["total_cost_dollars_per_hour"] == pytest.approx(
        reference["total_cost_dollars_per_hour"],
        abs=1e-2,
    )
