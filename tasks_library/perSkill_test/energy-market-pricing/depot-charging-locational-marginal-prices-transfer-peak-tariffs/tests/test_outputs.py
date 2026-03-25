import json
from collections import deque
from pathlib import Path


OUTPUT_FILE = Path("/root/charging_tariffs.json")
FEEDER_FILE = Path("/root/depot_feeder.json")
DEMAND_FILE = Path("/root/charging_demand.json")


class Edge:
    def __init__(self, to, rev, cap):
        self.to = to
        self.rev = rev
        self.cap = cap


def add_edge(graph, src, dst, cap):
    graph.setdefault(src, [])
    graph.setdefault(dst, [])
    graph[src].append(Edge(dst, len(graph[dst]), cap))
    graph[dst].append(Edge(src, len(graph[src]) - 1, 0))


def build_graph(lines, zones, demands_by_zone, hour, max_import):
    graph = {}
    add_edge(graph, "source", "substation", max_import)
    for line in lines:
        add_edge(graph, line["from_bus"], line["to_bus"], line["limit_mwh_per_hour"])
    for zone in zones:
        demand = demands_by_zone[zone["zone"]][hour]
        demand_node = f"demand:{zone['zone']}"
        add_edge(graph, zone["bus_id"], demand_node, demand)
        add_edge(graph, demand_node, "sink", demand)
    return graph


def solve_hour(lines, zones, demands_by_zone, hour, max_import, grid_price, backup_price):
    graph = build_graph(lines, zones, demands_by_zone, hour, max_import)
    main_supply = 0

    while True:
        parent = {"source": None}
        parent_edge = {}
        queue = deque(["source"])
        while queue and "sink" not in parent:
            node = queue.popleft()
            for edge_idx, edge in enumerate(graph.get(node, [])):
                if edge.cap > 0 and edge.to not in parent:
                    parent[edge.to] = node
                    parent_edge[edge.to] = edge_idx
                    queue.append(edge.to)
        if "sink" not in parent:
            break

        bottleneck = 10**9
        node = "sink"
        while parent[node] is not None:
            prev = parent[node]
            edge = graph[prev][parent_edge[node]]
            bottleneck = min(bottleneck, edge.cap)
            node = prev

        node = "sink"
        while parent[node] is not None:
            prev = parent[node]
            edge = graph[prev][parent_edge[node]]
            edge.cap -= bottleneck
            reverse = graph[edge.to][edge.rev]
            reverse.cap += bottleneck
            node = prev

        main_supply += bottleneck

    reachable = {"source"}
    queue = deque(["source"])
    while queue:
        node = queue.popleft()
        for edge in graph.get(node, []):
            if edge.cap > 0 and edge.to not in reachable:
                reachable.add(edge.to)
                queue.append(edge.to)

    tariffs = {}
    for zone in zones:
        tariffs[zone["zone"]] = round(
            float(grid_price if zone["bus_id"] in reachable else backup_price),
            2,
        )

    total_demand = sum(demands_by_zone[zone["zone"]][hour] for zone in zones)
    local_backup = total_demand - main_supply
    hour_cost = round(main_supply * grid_price + local_backup * backup_price, 2)
    return hour_cost, tariffs


def solve_case(lines, feeder, zones, demands_by_zone):
    max_import = feeder["grid_connection"]["max_import_mwh_per_hour"]
    prices = feeder["grid_connection"]["hourly_energy_price_dollars_per_MWh"]
    backup_price = feeder["local_backup_price_dollars_per_MWh"]

    zone_tariffs = {zone["zone"]: [] for zone in zones}
    total_cost = 0.0

    for hour, grid_price in enumerate(prices):
        hour_cost, tariffs = solve_hour(
            lines=lines,
            zones=zones,
            demands_by_zone=demands_by_zone,
            hour=hour,
            max_import=max_import,
            grid_price=grid_price,
            backup_price=backup_price,
        )
        total_cost += hour_cost
        for zone_name, tariff in tariffs.items():
            zone_tariffs[zone_name].append(tariff)

    zone_hourly_tariffs = []
    peak_hour_by_zone = []
    for zone in sorted(zones, key=lambda item: item["zone"]):
        tariff_series = zone_tariffs[zone["zone"]]
        peak_tariff = max(tariff_series)
        peak_hour = tariff_series.index(peak_tariff)
        zone_hourly_tariffs.append(
            {
                "zone": zone["zone"],
                "bus_id": zone["bus_id"],
                "tariffs_dollars_per_MWh": [round(float(value), 2) for value in tariff_series],
            }
        )
        peak_hour_by_zone.append(
            {
                "zone": zone["zone"],
                "bus_id": zone["bus_id"],
                "peak_hour": peak_hour,
                "peak_tariff_dollars_per_MWh": round(float(peak_tariff), 2),
            }
        )

    return {
        "total_charging_cost_dollars": round(float(total_cost), 2),
        "zone_hourly_tariffs": zone_hourly_tariffs,
        "peak_hour_by_zone": peak_hour_by_zone,
    }


def expected_report():
    feeder = json.loads(FEEDER_FILE.read_text())
    demand_data = json.loads(DEMAND_FILE.read_text())
    zones = sorted(demand_data["zones"], key=lambda item: item["zone"])
    demands_by_zone = {
        zone["zone"]: zone["hourly_demand_mwh"]
        for zone in demand_data["zones"]
    }

    baseline = solve_case(
        lines=feeder["baseline_lines"],
        feeder=feeder,
        zones=zones,
        demands_by_zone=demands_by_zone,
    )
    bypass_cable = solve_case(
        lines=feeder["baseline_lines"] + [feeder["temporary_bypass"]],
        feeder=feeder,
        zones=zones,
        demands_by_zone=demands_by_zone,
    )

    baseline_peaks = {
        entry["zone"]: entry["peak_tariff_dollars_per_MWh"]
        for entry in baseline["peak_hour_by_zone"]
    }
    bypass_peaks = {
        entry["zone"]: entry["peak_tariff_dollars_per_MWh"]
        for entry in bypass_cable["peak_hour_by_zone"]
    }

    drops = []
    for zone in sorted(baseline_peaks):
        baseline_peak = baseline_peaks[zone]
        bypass_peak = bypass_peaks[zone]
        drops.append(
            {
                "zone": zone,
                "baseline_peak_tariff_dollars_per_MWh": baseline_peak,
                "bypass_peak_tariff_dollars_per_MWh": bypass_peak,
                "drop_dollars_per_MWh": round(float(baseline_peak - bypass_peak), 2),
            }
        )

    return {
        "baseline": baseline,
        "bypass_cable": bypass_cable,
        "comparison": {
            "cost_reduction_dollars": round(
                baseline["total_charging_cost_dollars"] - bypass_cable["total_charging_cost_dollars"],
                2,
            ),
            "largest_peak_tariff_drops": sorted(
                drops,
                key=lambda item: (-item["drop_dollars_per_MWh"], item["zone"]),
            )[:3],
        },
    }


def assert_schema(report, zones):
    assert sorted(report.keys()) == ["baseline", "bypass_cable", "comparison"]

    for case_name in ["baseline", "bypass_cable"]:
        case = report[case_name]
        assert sorted(case.keys()) == [
            "peak_hour_by_zone",
            "total_charging_cost_dollars",
            "zone_hourly_tariffs",
        ]
        assert len(case["zone_hourly_tariffs"]) == len(zones)
        assert len(case["peak_hour_by_zone"]) == len(zones)

        zone_order = [zone["zone"] for zone in zones]
        assert [entry["zone"] for entry in case["zone_hourly_tariffs"]] == zone_order
        assert [entry["zone"] for entry in case["peak_hour_by_zone"]] == zone_order

        for entry in case["zone_hourly_tariffs"]:
            assert sorted(entry.keys()) == ["bus_id", "tariffs_dollars_per_MWh", "zone"]
            assert len(entry["tariffs_dollars_per_MWh"]) == 24

        for entry in case["peak_hour_by_zone"]:
            assert sorted(entry.keys()) == [
                "bus_id",
                "peak_hour",
                "peak_tariff_dollars_per_MWh",
                "zone",
            ]
            assert 0 <= entry["peak_hour"] <= 23

    comparison = report["comparison"]
    assert sorted(comparison.keys()) == [
        "cost_reduction_dollars",
        "largest_peak_tariff_drops",
    ]
    assert len(comparison["largest_peak_tariff_drops"]) == 3


def assert_matches_expected(report, expected):
    assert report == expected


def main():
    assert OUTPUT_FILE.exists(), "charging_tariffs.json 不存在"

    feeder = json.loads(FEEDER_FILE.read_text())
    demand_data = json.loads(DEMAND_FILE.read_text())
    zones = sorted(demand_data["zones"], key=lambda item: item["zone"])

    report = json.loads(OUTPUT_FILE.read_text())
    expected = expected_report()

    assert_schema(report, zones)
    assert_matches_expected(report, expected)


if __name__ == "__main__":
    main()
