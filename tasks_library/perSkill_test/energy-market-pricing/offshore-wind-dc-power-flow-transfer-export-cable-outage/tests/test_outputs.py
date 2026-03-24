import json
import math
import os

import numpy as np
import pytest

OUTPUT_FILE = "/root/offshore_cable_stress_report.json"
GRID_FILE = "/root/offshore_grid.json"
SCENARIO_FILE = "/root/maintenance_outage.json"


def rounded(value):
    return round(float(value), 4)


def compute_expected_report(grid, scenario):
    base_mva = float(grid["baseMVA"])
    nodes = grid["nodes"]
    cables = grid["cables"]
    slack_node = int(grid["slack_node"])
    landing_points = [int(node) for node in grid["landing_points"]]
    export_cable_ids = list(grid["export_cable_ids"])
    maintenance_outage_cable_id = scenario["maintenance_outage_cable_id"]
    loading_alert_pct = float(scenario["loading_alert_pct"])
    top_rerouted_count = int(scenario["top_rerouted_count"])

    node_order = [int(node["node"]) for node in nodes]
    node_to_idx = {node_id: idx for idx, node_id in enumerate(node_order)}
    slack_idx = node_to_idx[slack_node]
    injections_mw = np.array([float(node["net_injection_MW"]) for node in nodes], dtype=float)

    def solve_case(outaged_cable_id=None):
        n_nodes = len(node_order)
        b_matrix = np.zeros((n_nodes, n_nodes), dtype=float)
        active_flags = []

        for cable in cables:
            is_active = cable["cable_id"] != outaged_cable_id
            active_flags.append(is_active)
            if not is_active:
                continue

            from_idx = node_to_idx[int(cable["from_node"])]
            to_idx = node_to_idx[int(cable["to_node"])]
            susceptance = 1.0 / float(cable["x_pu"])

            b_matrix[from_idx, from_idx] += susceptance
            b_matrix[to_idx, to_idx] += susceptance
            b_matrix[from_idx, to_idx] -= susceptance
            b_matrix[to_idx, from_idx] -= susceptance

        keep = [idx for idx in range(n_nodes) if idx != slack_idx]
        theta = np.zeros(n_nodes, dtype=float)
        theta[keep] = np.linalg.solve(
            b_matrix[np.ix_(keep, keep)],
            injections_mw[keep] / base_mva,
        )

        flow_entries = []
        flow_by_id = {}
        for cable, is_active in zip(cables, active_flags):
            if not is_active:
                continue

            from_node = int(cable["from_node"])
            to_node = int(cable["to_node"])
            from_idx = node_to_idx[from_node]
            to_idx = node_to_idx[to_node]
            flow_mw = (theta[from_idx] - theta[to_idx]) / float(cable["x_pu"]) * base_mva
            rating_mw = float(cable["rating_MW"])

            entry = {
                "cable_id": cable["cable_id"],
                "from_node": from_node,
                "to_node": to_node,
                "flow_MW": rounded(flow_mw),
                "rating_MW": rounded(rating_mw),
                "loading_pct": rounded(abs(flow_mw) / rating_mw * 100.0),
                "cable_type": cable["cable_type"],
            }
            flow_entries.append(entry)
            flow_by_id[cable["cable_id"]] = entry

        return {
            "theta": theta,
            "flow_entries": flow_entries,
            "flow_by_id": flow_by_id,
        }

    normal_case = solve_case()
    maintenance_case = solve_case(outaged_cable_id=maintenance_outage_cable_id)

    normal_export_cable_loadings = [
        {key: value for key, value in normal_case["flow_by_id"][cable_id].items() if key != "cable_type"}
        for cable_id in export_cable_ids
    ]
    maintenance_export_cable_loadings = [
        {key: value for key, value in maintenance_case["flow_by_id"][cable_id].items() if key != "cable_type"}
        for cable_id in export_cable_ids
        if cable_id in maintenance_case["flow_by_id"]
    ]

    normal_overloads = [
        entry
        for entry in normal_case["flow_entries"]
        if entry["loading_pct"] >= loading_alert_pct
    ]
    maintenance_overloads = [
        entry
        for entry in maintenance_case["flow_entries"]
        if entry["loading_pct"] >= loading_alert_pct
    ]

    landing_point_angle_shifts = []
    for node in landing_points:
        normal_angle_deg = normal_case["theta"][node_to_idx[node]] * 180.0 / math.pi
        maintenance_angle_deg = maintenance_case["theta"][node_to_idx[node]] * 180.0 / math.pi
        landing_point_angle_shifts.append(
            {
                "node": node,
                "normal_angle_deg": rounded(normal_angle_deg),
                "maintenance_angle_deg": rounded(maintenance_angle_deg),
                "absolute_shift_deg": rounded(abs(maintenance_angle_deg - normal_angle_deg)),
            }
        )

    landing_point_angle_shifts.sort(key=lambda item: (-item["absolute_shift_deg"], item["node"]))

    largest_rerouted_cables = []
    for cable in cables:
        cable_id = cable["cable_id"]
        if cable_id == maintenance_outage_cable_id:
            continue

        normal_flow = normal_case["flow_by_id"][cable_id]["flow_MW"]
        maintenance_flow = maintenance_case["flow_by_id"][cable_id]["flow_MW"]
        largest_rerouted_cables.append(
            {
                "cable_id": cable_id,
                "cable_type": cable["cable_type"],
                "from_node": int(cable["from_node"]),
                "to_node": int(cable["to_node"]),
                "normal_flow_MW": normal_flow,
                "maintenance_flow_MW": maintenance_flow,
                "absolute_delta_MW": rounded(abs(maintenance_flow - normal_flow)),
            }
        )

    largest_rerouted_cables.sort(key=lambda item: (-item["absolute_delta_MW"], item["cable_id"]))

    normal_overload_ids = {entry["cable_id"] for entry in normal_overloads}
    maintenance_overload_ids = {entry["cable_id"] for entry in maintenance_overloads}
    outaged_cable = next(cable for cable in cables if cable["cable_id"] == maintenance_outage_cable_id)

    return {
        "scenario": {
            "name": scenario["scenario_name"],
            "slack_node": slack_node,
            "maintenance_outage_cable_id": maintenance_outage_cable_id,
            "maintenance_outage": {
                "cable_id": outaged_cable["cable_id"],
                "from_node": int(outaged_cable["from_node"]),
                "to_node": int(outaged_cable["to_node"]),
                "cable_type": outaged_cable["cable_type"],
            },
        },
        "normal_topology": {
            "export_cable_loadings": normal_export_cable_loadings,
            "overloaded_elements": normal_overloads,
        },
        "maintenance_topology": {
            "export_cable_loadings": maintenance_export_cable_loadings,
            "overloaded_elements": maintenance_overloads,
        },
        "comparison": {
            "landing_point_angle_shifts_deg": landing_point_angle_shifts,
            "largest_rerouted_cables": largest_rerouted_cables[:top_rerouted_count],
            "newly_overloaded_elements": sorted(maintenance_overload_ids - normal_overload_ids),
        },
    }


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def grid():
    with open(GRID_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def scenario():
    with open(SCENARIO_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_report(grid, scenario):
    return compute_expected_report(grid, scenario)


class TestSchema:
    def test_top_level_fields(self, report):
        assert sorted(report.keys()) == ["comparison", "maintenance_topology", "normal_topology", "scenario"]

    def test_export_loading_lengths(self, report, grid):
        assert len(report["normal_topology"]["export_cable_loadings"]) == len(grid["export_cable_ids"])
        assert len(report["maintenance_topology"]["export_cable_loadings"]) == len(grid["export_cable_ids"]) - 1

    def test_overload_lists_present(self, report):
        assert isinstance(report["normal_topology"]["overloaded_elements"], list)
        assert isinstance(report["maintenance_topology"]["overloaded_elements"], list)


class TestNumerics:
    def test_report_matches_expected(self, report, expected_report):
        assert report == expected_report

    def test_normal_topology_has_no_overloads(self, report):
        assert report["normal_topology"]["overloaded_elements"] == []

    def test_newly_overloaded_elements(self, report):
        assert report["comparison"]["newly_overloaded_elements"] == ["E2", "E3", "T1"]

    def test_top_rerouted_cable(self, report):
        top_entry = report["comparison"]["largest_rerouted_cables"][0]
        assert top_entry["cable_id"] == "T1"
        assert top_entry["absolute_delta_MW"] == pytest.approx(225.1649, abs=1e-4)
