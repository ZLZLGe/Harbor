import json
import os

import numpy as np
import pytest

CASE_PATH = "/root/corridor_case.json"
OUTPUT_PATH = "/root/contingency_risk_rankings.json"
DELTA_THRESHOLD = 5.0
TOL = 1e-2


def build_flow_solution(case, active_branches):
    buses = case["buses"]
    base_mva = float(case["baseMVA"])
    bus_index = {int(bus["id"]): idx for idx, bus in enumerate(buses)}
    slack_idx = next(idx for idx, bus in enumerate(buses) if bus["type"] == "slack")

    injections = np.array(
        [
            (float(bus["generation_MW"]) - float(bus["load_MW"])) / base_mva
            for bus in buses
        ],
        dtype=float,
    )
    assert abs(np.sum(injections)) <= 1e-9, "Base injections must balance"

    n_bus = len(buses)
    bmat = np.zeros((n_bus, n_bus), dtype=float)
    for branch in active_branches:
        f = bus_index[int(branch["from"])]
        t = bus_index[int(branch["to"])]
        susceptance = 1.0 / float(branch["x_pu"])
        bmat[f, f] += susceptance
        bmat[t, t] += susceptance
        bmat[f, t] -= susceptance
        bmat[t, f] -= susceptance

    keep = [idx for idx in range(n_bus) if idx != slack_idx]
    theta = np.zeros(n_bus, dtype=float)
    theta[keep] = np.linalg.solve(bmat[np.ix_(keep, keep)], injections[keep])

    line_results = {}
    for branch in active_branches:
        f = bus_index[int(branch["from"])]
        t = bus_index[int(branch["to"])]
        flow_mw = base_mva * (theta[f] - theta[t]) / float(branch["x_pu"])
        loading_pct = abs(flow_mw) / float(branch["limit_MW"]) * 100.0
        line_results[branch["id"]] = {
            "id": branch["id"],
            "from": int(branch["from"]),
            "to": int(branch["to"]),
            "flow_MW": float(flow_mw),
            "limit_MW": float(branch["limit_MW"]),
            "loading_pct": float(loading_pct),
            "over_limit_pct": float(max(loading_pct - 100.0, 0.0)),
        }
    return line_results


def build_interface_rows(case, line_results, base_loading_map=None):
    rows = []
    for interface in case["interfaces"]:
        flow_mw = 0.0
        for element in interface["elements"]:
            branch = line_results.get(element["branch_id"])
            element_flow = 0.0 if branch is None else branch["flow_MW"]
            flow_mw += float(element["sign"]) * element_flow

        loading_pct = abs(flow_mw) / float(interface["limit_MW"]) * 100.0
        row = {
            "id": interface["id"],
            "flow_MW": float(flow_mw),
            "limit_MW": float(interface["limit_MW"]),
            "loading_pct": float(loading_pct),
        }
        if base_loading_map is not None:
            row["delta_loading_pct"] = float(loading_pct - base_loading_map[interface["id"]])
        rows.append(row)
    return rows


def build_reference(case):
    base_lines = build_flow_solution(case, case["branches"])
    base_interfaces = build_interface_rows(case, base_lines)
    base_loading_map = {row["id"]: row["loading_pct"] for row in base_interfaces}

    scenario_results = []
    for contingency in case["contingencies"]:
        active_branches = [
            branch
            for branch in case["branches"]
            if branch["id"] != contingency["outaged_branch_id"]
        ]
        line_results = build_flow_solution(case, active_branches)
        most_loaded = min(
            ((-row["loading_pct"], row["id"], row) for row in line_results.values())
        )[2]

        affected_interfaces = []
        for row in build_interface_rows(case, line_results, base_loading_map):
            if abs(row["delta_loading_pct"]) + 1e-9 < DELTA_THRESHOLD:
                continue
            affected_interfaces.append(
                {
                    "id": row["id"],
                    "flow_MW": round(float(row["flow_MW"]), 2),
                    "limit_MW": round(float(row["limit_MW"]), 2),
                    "loading_pct": round(float(row["loading_pct"]), 2),
                    "delta_loading_pct": round(float(row["delta_loading_pct"]), 2),
                }
            )

        affected_interfaces.sort(
            key=lambda item: (-abs(item["delta_loading_pct"]), item["id"])
        )

        scenario_results.append(
            {
                "scenario_id": contingency["id"],
                "outaged_branch_id": contingency["outaged_branch_id"],
                "most_loaded_line": {
                    "id": most_loaded["id"],
                    "from": most_loaded["from"],
                    "to": most_loaded["to"],
                    "flow_MW": round(float(most_loaded["flow_MW"]), 2),
                    "limit_MW": round(float(most_loaded["limit_MW"]), 2),
                    "loading_pct": round(float(most_loaded["loading_pct"]), 2),
                    "over_limit_pct": round(float(most_loaded["over_limit_pct"]), 2),
                },
                "max_over_limit_pct": round(float(most_loaded["over_limit_pct"]), 2),
                "affected_interfaces": affected_interfaces,
            }
        )

    top_3 = sorted(
        scenario_results,
        key=lambda item: (-item["max_over_limit_pct"], item["scenario_id"]),
    )[:3]

    return {
        "case_id": case["case_id"],
        "scenario_results": scenario_results,
        "top_3_riskiest_scenarios": [
            {
                "scenario_id": row["scenario_id"],
                "outaged_branch_id": row["outaged_branch_id"],
                "max_over_limit_pct": row["max_over_limit_pct"],
                "most_loaded_line_id": row["most_loaded_line"]["id"],
            }
            for row in top_3
        ],
    }


@pytest.fixture(scope="module")
def case():
    with open(CASE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_PATH), f"Missing output file: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference(case):
    return build_reference(case)


def test_schema(case, report):
    assert report["case_id"] == case["case_id"]
    assert isinstance(report["scenario_results"], list)
    assert isinstance(report["top_3_riskiest_scenarios"], list)
    assert len(report["scenario_results"]) == len(case["contingencies"])
    assert len(report["top_3_riskiest_scenarios"]) == 3

    for row in report["scenario_results"]:
        assert set(row.keys()) == {
            "scenario_id",
            "outaged_branch_id",
            "most_loaded_line",
            "max_over_limit_pct",
            "affected_interfaces",
        }
        assert isinstance(row["affected_interfaces"], list)
        line = row["most_loaded_line"]
        assert set(line.keys()) == {
            "id",
            "from",
            "to",
            "flow_MW",
            "limit_MW",
            "loading_pct",
            "over_limit_pct",
        }
        for interface in row["affected_interfaces"]:
            assert set(interface.keys()) == {
                "id",
                "flow_MW",
                "limit_MW",
                "loading_pct",
                "delta_loading_pct",
            }

    for row in report["top_3_riskiest_scenarios"]:
        assert set(row.keys()) == {
            "scenario_id",
            "outaged_branch_id",
            "max_over_limit_pct",
            "most_loaded_line_id",
        }


def test_scenario_results(case, report, reference):
    expected_ids = [row["id"] for row in case["contingencies"]]
    actual_ids = [row["scenario_id"] for row in report["scenario_results"]]
    assert actual_ids == expected_ids

    reference_map = {
        row["scenario_id"]: row for row in reference["scenario_results"]
    }

    for actual in report["scenario_results"]:
        expected = reference_map[actual["scenario_id"]]
        assert actual["outaged_branch_id"] == expected["outaged_branch_id"]
        assert actual["max_over_limit_pct"] == pytest.approx(
            expected["max_over_limit_pct"], abs=TOL
        )

        actual_line = actual["most_loaded_line"]
        expected_line = expected["most_loaded_line"]
        assert actual_line["id"] == expected_line["id"]
        assert actual_line["from"] == expected_line["from"]
        assert actual_line["to"] == expected_line["to"]
        for key in ["flow_MW", "limit_MW", "loading_pct", "over_limit_pct"]:
            assert actual_line[key] == pytest.approx(expected_line[key], abs=TOL)

        actual_interfaces = actual["affected_interfaces"]
        expected_interfaces = expected["affected_interfaces"]
        assert [row["id"] for row in actual_interfaces] == [
            row["id"] for row in expected_interfaces
        ]
        for actual_iface, expected_iface in zip(actual_interfaces, expected_interfaces):
            for key in ["flow_MW", "limit_MW", "loading_pct", "delta_loading_pct"]:
                assert actual_iface[key] == pytest.approx(expected_iface[key], abs=TOL)


def test_top_3_ranking(report, reference):
    actual_rows = report["top_3_riskiest_scenarios"]
    expected_rows = reference["top_3_riskiest_scenarios"]
    assert len(actual_rows) == len(expected_rows)

    for actual, expected in zip(actual_rows, expected_rows):
        assert actual["scenario_id"] == expected["scenario_id"]
        assert actual["outaged_branch_id"] == expected["outaged_branch_id"]
        assert actual["most_loaded_line_id"] == expected["most_loaded_line_id"]
        assert actual["max_over_limit_pct"] == pytest.approx(
            expected["max_over_limit_pct"], abs=TOL
        )
