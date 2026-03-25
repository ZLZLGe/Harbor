import json
import heapq
from itertools import count
from math import inf
from pathlib import Path


OUTPUT_FILE = Path("/root/restoration_service_prices.json")
ASSETS_FILE = Path("/root/microgrid_assets.json")
PLAN_FILE = Path("/root/repair_plan.json")
EPSILON_MWH = 1e-3


class Edge:
    def __init__(self, to_node, reverse_index, capacity, cost):
        self.to_node = to_node
        self.reverse_index = reverse_index
        self.capacity = capacity
        self.cost = cost


def add_edge(graph, source, target, capacity, cost):
    graph.setdefault(source, [])
    graph.setdefault(target, [])
    graph[source].append(Edge(target, len(graph[target]), capacity, cost))
    graph[target].append(Edge(source, len(graph[source]) - 1, 0.0, -cost))


def build_graph(assets, lines, extra_injection_bus=None, extra_injection_mwh=0.0):
    graph = {}
    source = "source"
    sink = "sink"

    for resource in assets["dispatchable_resources"]:
        resource_node = ("resource", resource["resource_id"])
        bus_node = ("bus", resource["bus_id"])
        cap = float(resource["max_output_mw"])
        cost = float(resource["marginal_cost_dollars_per_mwh"])
        add_edge(graph, source, resource_node, cap, cost)
        add_edge(graph, resource_node, bus_node, cap, 0.0)

    if extra_injection_bus is not None and extra_injection_mwh > 0:
        add_edge(graph, source, ("bus", extra_injection_bus), extra_injection_mwh, 0.0)

    for line in lines:
        add_edge(
            graph,
            ("bus", line["from_bus"]),
            ("bus", line["to_bus"]),
            float(line["limit_mw"]),
            0.0,
        )

    for bus in assets["buses"]:
        demand = float(bus["demand_mw"])
        if demand > 0:
            add_edge(
                graph,
                ("bus", bus["bus_id"]),
                sink,
                demand,
                -float(bus["unserved_penalty_dollars_per_mwh"]),
            )

    return graph, source, sink


def solve_restoration(assets, lines, extra_injection_bus=None, extra_injection_mwh=0.0):
    graph, source, sink = build_graph(
        assets,
        lines,
        extra_injection_bus=extra_injection_bus,
        extra_injection_mwh=extra_injection_mwh,
    )
    potentials = {node: 0.0 for node in graph}
    ticket = count()
    total_flow = 0.0
    transformed_objective = 0.0

    while True:
        distance = {node: inf for node in graph}
        previous_node = {}
        previous_edge_index = {}
        distance[source] = 0.0
        queue = [(0.0, next(ticket), source)]

        while queue:
            current_distance, _, node = heapq.heappop(queue)
            if current_distance != distance[node]:
                continue
            for edge_index, edge in enumerate(graph[node]):
                if edge.capacity <= 1e-12:
                    continue
                next_distance = (
                    current_distance
                    + edge.cost
                    + potentials[node]
                    - potentials[edge.to_node]
                )
                if next_distance < distance[edge.to_node] - 1e-12:
                    distance[edge.to_node] = next_distance
                    previous_node[edge.to_node] = node
                    previous_edge_index[edge.to_node] = edge_index
                    heapq.heappush(queue, (next_distance, next(ticket), edge.to_node))

        if distance[sink] == inf:
            break

        for node, value in distance.items():
            if value < inf:
                potentials[node] += value

        path_cost = potentials[sink] - potentials[source]
        if path_cost >= -1e-12:
            break

        augment = inf
        node = sink
        while node != source:
            prev = previous_node[node]
            edge = graph[prev][previous_edge_index[node]]
            augment = min(augment, edge.capacity)
            node = prev

        node = sink
        while node != source:
            prev = previous_node[node]
            edge = graph[prev][previous_edge_index[node]]
            edge.capacity -= augment
            reverse = graph[node][edge.reverse_index]
            reverse.capacity += augment
            node = prev

        total_flow += augment
        transformed_objective += augment * path_cost

    total_penalty_constant = sum(
        float(bus["demand_mw"]) * float(bus["unserved_penalty_dollars_per_mwh"])
        for bus in assets["buses"]
    )
    true_objective = total_penalty_constant + transformed_objective
    return {
        "objective_dollars": true_objective,
        "total_restored_load_mw": total_flow,
    }


def rounded(value):
    return round(float(value), 2)


def build_case_report(assets, lines):
    solved = solve_restoration(assets, lines)
    values = {}
    for bus in assets["buses"]:
        perturbed = solve_restoration(
            assets,
            lines,
            extra_injection_bus=bus["bus_id"],
            extra_injection_mwh=EPSILON_MWH,
        )
        values[bus["bus_id"]] = rounded(
            (solved["objective_dollars"] - perturbed["objective_dollars"]) / EPSILON_MWH
        )

    bus_values = [
        {
            "bus_id": bus["bus_id"],
            "marginal_service_value_dollars_per_mwh": values[bus["bus_id"]],
        }
        for bus in sorted(assets["buses"], key=lambda item: item["bus_id"])
    ]

    islands = {}
    for bus in assets["buses"]:
        if float(bus["demand_mw"]) <= 0:
            continue
        value = values[bus["bus_id"]]
        islands.setdefault(value, []).append(bus["bus_id"])

    price_islands = [
        {
            "marginal_service_value_dollars_per_mwh": rounded(value),
            "buses": sorted(bus_ids),
        }
        for value, bus_ids in sorted(islands.items(), key=lambda item: item[0])
    ]

    return {
        "total_restored_load_mw": rounded(solved["total_restored_load_mw"]),
        "price_island_count": len(price_islands),
        "bus_marginal_service_values": bus_values,
        "price_islands": price_islands,
    }


def value_map(case_report):
    return {
        entry["bus_id"]: entry["marginal_service_value_dollars_per_mwh"]
        for entry in case_report["bus_marginal_service_values"]
    }


def expected_report():
    assets = json.loads(ASSETS_FILE.read_text(encoding="utf-8"))
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))

    baseline = build_case_report(assets, assets["baseline_lines"])
    tie_repaired = build_case_report(
        assets,
        assets["baseline_lines"] + [plan["repairable_tie_line"]],
    )

    baseline_values = value_map(baseline)
    tie_values = value_map(tie_repaired)

    shelter_value_changes = []
    for bus_id in sorted(plan["observed_shelter_buses"]):
        shelter_value_changes.append(
            {
                "bus_id": bus_id,
                "baseline_marginal_service_value_dollars_per_mwh": baseline_values[bus_id],
                "tie_repaired_marginal_service_value_dollars_per_mwh": tie_values[bus_id],
                "change_dollars_per_mwh": rounded(tie_values[bus_id] - baseline_values[bus_id]),
            }
        )

    split_a, split_b = plan["split_check_pair"]
    return {
        "baseline": baseline,
        "tie_repaired": tie_repaired,
        "restoration_comparison": {
            "restored_load_gain_mw": rounded(
                tie_repaired["total_restored_load_mw"] - baseline["total_restored_load_mw"]
            ),
            "shelter_value_changes": shelter_value_changes,
            "repair_line_eliminated_original_price_split": (
                baseline_values[split_a] != baseline_values[split_b]
                and tie_values[split_a] == tie_values[split_b]
            ),
        },
    }


def test_output_exists():
    assert OUTPUT_FILE.exists(), "restoration_service_prices.json 不存在"


def test_schema_and_ordering():
    report = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    assets = json.loads(ASSETS_FILE.read_text(encoding="utf-8"))
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))

    assert sorted(report.keys()) == ["baseline", "restoration_comparison", "tie_repaired"]

    all_bus_ids = sorted(bus["bus_id"] for bus in assets["buses"])
    demand_bus_ids = sorted(
        bus["bus_id"] for bus in assets["buses"] if float(bus["demand_mw"]) > 0
    )

    for case_name in ["baseline", "tie_repaired"]:
        case = report[case_name]
        assert sorted(case.keys()) == [
            "bus_marginal_service_values",
            "price_island_count",
            "price_islands",
            "total_restored_load_mw",
        ]
        assert isinstance(case["price_island_count"], int)
        assert case["price_island_count"] == len(case["price_islands"])
        assert [entry["bus_id"] for entry in case["bus_marginal_service_values"]] == all_bus_ids

        island_buses = []
        previous_value = None
        for island in case["price_islands"]:
            assert sorted(island.keys()) == [
                "buses",
                "marginal_service_value_dollars_per_mwh",
            ]
            assert island["buses"] == sorted(island["buses"])
            island_buses.extend(island["buses"])
            value = island["marginal_service_value_dollars_per_mwh"]
            if previous_value is not None:
                assert value >= previous_value
            previous_value = value
        assert sorted(island_buses) == demand_bus_ids

    comparison = report["restoration_comparison"]
    assert sorted(comparison.keys()) == [
        "repair_line_eliminated_original_price_split",
        "restored_load_gain_mw",
        "shelter_value_changes",
    ]
    assert [
        entry["bus_id"] for entry in comparison["shelter_value_changes"]
    ] == sorted(plan["observed_shelter_buses"])


def test_report_matches_expected_semantics():
    report = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    assert report == expected_report()
