import json
import math
import os

import numpy as np
import pytest

OUTPUT_FILE = "/root/contingency_flow_report.json"
SNAPSHOT_FILE = "/root/transmission_snapshot.json"
CONTINGENCY_FILE = "/root/contingency.json"


def rounded(value):
    return round(float(value), 4)


def compute_expected_report(snapshot, contingency):
    base_mva = float(snapshot["baseMVA"])
    buses = snapshot["buses"]
    branches = snapshot["branches"]
    slack_bus = int(snapshot["slack_bus"])
    outaged_branch_id = contingency["outaged_branch_id"]
    overload_threshold = float(contingency["overload_threshold_pct"])
    top_angle_shift_count = int(contingency["top_angle_shift_count"])
    top_flow_redistribution_count = int(contingency["top_flow_redistribution_count"])

    bus_order = [int(bus["bus"]) for bus in buses]
    bus_num_to_idx = {bus_num: idx for idx, bus_num in enumerate(bus_order)}
    slack_idx = bus_num_to_idx[slack_bus]
    injections_mw = np.array([float(bus["net_injection_MW"]) for bus in buses], dtype=float)

    def solve_case(outaged_id=None):
        n_bus = len(buses)
        b_matrix = np.zeros((n_bus, n_bus), dtype=float)
        active_branch_flags = []

        for branch in branches:
            is_active = branch["branch_id"] != outaged_id
            active_branch_flags.append(is_active)
            if not is_active:
                continue

            from_idx = bus_num_to_idx[int(branch["from_bus"])]
            to_idx = bus_num_to_idx[int(branch["to_bus"])]
            susceptance = 1.0 / float(branch["x_pu"])

            b_matrix[from_idx, from_idx] += susceptance
            b_matrix[to_idx, to_idx] += susceptance
            b_matrix[from_idx, to_idx] -= susceptance
            b_matrix[to_idx, from_idx] -= susceptance

        keep = [idx for idx in range(n_bus) if idx != slack_idx]
        theta = np.zeros(n_bus, dtype=float)
        theta[keep] = np.linalg.solve(
            b_matrix[np.ix_(keep, keep)],
            injections_mw[keep] / base_mva,
        )

        angle_entries = [
            {"bus": int(bus_num), "angle_deg": rounded(theta[bus_num_to_idx[bus_num]] * 180.0 / math.pi)}
            for bus_num in bus_order
        ]

        branch_flow_entries = []
        overload_entries = []
        flow_by_branch_id = {}

        for branch, is_active in zip(branches, active_branch_flags):
            if not is_active:
                continue

            from_bus = int(branch["from_bus"])
            to_bus = int(branch["to_bus"])
            from_idx = bus_num_to_idx[from_bus]
            to_idx = bus_num_to_idx[to_bus]
            flow_mw = (
                (theta[from_idx] - theta[to_idx]) / float(branch["x_pu"]) * base_mva
            )
            limit_mw = float(branch["limit_MW"])
            loading_pct = abs(flow_mw) / limit_mw * 100.0

            flow_entry = {
                "branch_id": branch["branch_id"],
                "from_bus": from_bus,
                "to_bus": to_bus,
                "flow_MW": rounded(flow_mw),
                "limit_MW": rounded(limit_mw),
                "loading_pct": rounded(loading_pct),
            }
            branch_flow_entries.append(flow_entry)
            flow_by_branch_id[branch["branch_id"]] = flow_entry

            if loading_pct >= overload_threshold:
                overload_entries.append(flow_entry)

        return {
            "bus_angles_deg": angle_entries,
            "branch_flows": branch_flow_entries,
            "overloads": overload_entries,
            "flow_by_branch_id": flow_by_branch_id,
        }

    base_case = solve_case()
    outage_case = solve_case(outaged_id=outaged_branch_id)

    angle_shifts = []
    for bus_num in bus_order:
        base_angle = next(item["angle_deg"] for item in base_case["bus_angles_deg"] if item["bus"] == bus_num)
        outage_angle = next(item["angle_deg"] for item in outage_case["bus_angles_deg"] if item["bus"] == bus_num)
        angle_shifts.append(
            {
                "bus": bus_num,
                "base_angle_deg": base_angle,
                "outage_angle_deg": outage_angle,
                "absolute_shift_deg": rounded(abs(outage_angle - base_angle)),
            }
        )

    angle_shifts.sort(key=lambda item: (-item["absolute_shift_deg"], item["bus"]))

    flow_redistribution = []
    for branch in branches:
        branch_id = branch["branch_id"]
        if branch_id == outaged_branch_id:
            continue

        base_flow = base_case["flow_by_branch_id"][branch_id]["flow_MW"]
        outage_flow = outage_case["flow_by_branch_id"][branch_id]["flow_MW"]
        flow_redistribution.append(
            {
                "branch_id": branch_id,
                "from_bus": int(branch["from_bus"]),
                "to_bus": int(branch["to_bus"]),
                "base_flow_MW": base_flow,
                "outage_flow_MW": outage_flow,
                "absolute_delta_MW": rounded(abs(outage_flow - base_flow)),
            }
        )

    flow_redistribution.sort(key=lambda item: (-item["absolute_delta_MW"], item["branch_id"]))

    base_overloaded = {entry["branch_id"] for entry in base_case["overloads"]}
    outage_overloaded = {entry["branch_id"] for entry in outage_case["overloads"]}
    outaged_branch = next(branch for branch in branches if branch["branch_id"] == outaged_branch_id)

    return {
        "scenario": {
            "name": contingency["scenario_name"],
            "slack_bus": slack_bus,
            "outaged_branch_id": outaged_branch_id,
            "outaged_branch": {
                "branch_id": outaged_branch_id,
                "from_bus": int(outaged_branch["from_bus"]),
                "to_bus": int(outaged_branch["to_bus"]),
            },
        },
        "base_case": {
            "bus_angles_deg": base_case["bus_angles_deg"],
            "branch_flows": base_case["branch_flows"],
            "overloads": base_case["overloads"],
        },
        "outage_case": {
            "bus_angles_deg": outage_case["bus_angles_deg"],
            "branch_flows": outage_case["branch_flows"],
            "overloads": outage_case["overloads"],
        },
        "comparison": {
            "largest_angle_shifts": angle_shifts[:top_angle_shift_count],
            "largest_flow_redistribution": flow_redistribution[:top_flow_redistribution_count],
            "overload_count_change": len(outage_overloaded) - len(base_overloaded),
            "newly_overloaded_branches": sorted(outage_overloaded - base_overloaded),
        },
    }


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def snapshot():
    with open(SNAPSHOT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def contingency():
    with open(CONTINGENCY_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_report(snapshot, contingency):
    return compute_expected_report(snapshot, contingency)


class TestSchema:
    def test_top_level_fields(self, report):
        assert sorted(report.keys()) == ["base_case", "comparison", "outage_case", "scenario"]

    def test_case_lengths(self, report, snapshot):
        n_buses = len(snapshot["buses"])
        n_branches = len(snapshot["branches"])

        assert len(report["base_case"]["bus_angles_deg"]) == n_buses
        assert len(report["outage_case"]["bus_angles_deg"]) == n_buses
        assert len(report["base_case"]["branch_flows"]) == n_branches
        assert len(report["outage_case"]["branch_flows"]) == n_branches - 1


class TestNumerics:
    def test_matches_expected_report(self, report, expected_report):
        assert report == expected_report

    def test_power_balance_consistency(self, report, snapshot):
        branch_flow_map = {entry["branch_id"]: entry["flow_MW"] for entry in report["base_case"]["branch_flows"]}
        assert branch_flow_map["L1"] == pytest.approx(120.0, abs=1e-4)

        total_injection = sum(bus["net_injection_MW"] for bus in snapshot["buses"])
        assert total_injection == pytest.approx(0.0, abs=1e-9)

    def test_newly_overloaded_branches(self, report):
        assert report["comparison"]["newly_overloaded_branches"] == ["L2"]
