import itertools
import json
import os

import numpy as np
import pytest

CASE_PATH = "/root/offshore_export_case.json"
OUTPUT_PATH = "/root/offshore_curtailment_plan.json"
TOL = 1e-2


def rounded(value):
    value = float(value)
    if abs(value) < 5e-10:
        value = 0.0
    return round(value, 2)


def build_model(case):
    buses = case["buses"]
    stations = case["stations"]
    cables = case["cables"]
    base_mva = float(case["baseMVA"])

    slack_bus = next(bus for bus in buses if bus["type"] == "slack")
    slack_id = int(slack_bus["id"])
    non_slack = [int(bus["id"]) for bus in buses if int(bus["id"]) != slack_id]
    non_slack_index = {bus_id: idx for idx, bus_id in enumerate(non_slack)}

    b_reduced = np.zeros((len(non_slack), len(non_slack)), dtype=float)
    for cable in cables:
        f_bus = int(cable["from"])
        t_bus = int(cable["to"])
        susceptance = 1.0 / float(cable["x_pu"])

        if f_bus != slack_id:
            f_idx = non_slack_index[f_bus]
            b_reduced[f_idx, f_idx] += susceptance
        if t_bus != slack_id:
            t_idx = non_slack_index[t_bus]
            b_reduced[t_idx, t_idx] += susceptance
        if f_bus != slack_id and t_bus != slack_id:
            f_idx = non_slack_index[f_bus]
            t_idx = non_slack_index[t_bus]
            b_reduced[f_idx, t_idx] -= susceptance
            b_reduced[t_idx, f_idx] -= susceptance

    inverse_b = np.linalg.inv(b_reduced)

    ptdf_rows = []
    for cable in cables:
        row = []
        for station in stations:
            injections = np.zeros(len(non_slack), dtype=float)
            injections[non_slack_index[int(station["bus"])]] = 1.0 / base_mva
            theta = inverse_b @ injections

            theta_from = (
                0.0
                if int(cable["from"]) == slack_id
                else theta[non_slack_index[int(cable["from"])]]
            )
            theta_to = (
                0.0
                if int(cable["to"]) == slack_id
                else theta[non_slack_index[int(cable["to"])]]
            )
            flow_mw = base_mva * (theta_from - theta_to) / float(cable["x_pu"])
            row.append(flow_mw)
        ptdf_rows.append(row)

    return {
        "base_mva": base_mva,
        "slack_id": slack_id,
        "non_slack": non_slack,
        "non_slack_index": non_slack_index,
        "inverse_b": inverse_b,
        "ptdf": np.array(ptdf_rows, dtype=float),
    }


def enumerate_optimal_dispatch(case, model):
    stations = case["stations"]
    cables = case["cables"]
    station_count = len(stations)

    a_rows = []
    b_vals = []
    for idx, station in enumerate(stations):
        upper = np.zeros(station_count, dtype=float)
        upper[idx] = 1.0
        lower = np.zeros(station_count, dtype=float)
        lower[idx] = -1.0
        a_rows.extend([upper, lower])
        b_vals.extend([float(station["available_MW"]), 0.0])

    for row, cable in zip(model["ptdf"], cables):
        a_rows.extend([row, -row])
        b_vals.extend([float(cable["limit_MW"]), float(cable["limit_MW"])])

    a_matrix = np.array(a_rows, dtype=float)
    b_vector = np.array(b_vals, dtype=float)

    keep_value = np.array(
        [
            float(case["objective_total_curtailment_weight"])
            + float(station["priority_weight"])
            for station in stations
        ],
        dtype=float,
    )

    best_dispatch = None
    best_objective = None

    for combo in itertools.combinations(range(len(a_matrix)), station_count):
        basis = a_matrix[list(combo)]
        if np.linalg.matrix_rank(basis) < station_count:
            continue

        try:
            candidate = np.linalg.solve(basis, b_vector[list(combo)])
        except np.linalg.LinAlgError:
            continue

        if np.any(a_matrix @ candidate - b_vector > 1e-7):
            continue

        objective = float(keep_value @ candidate)
        if best_dispatch is None or objective > best_objective + 1e-9:
            best_dispatch = candidate
            best_objective = objective

    assert best_dispatch is not None, "reference optimization failed"
    return np.where(np.abs(best_dispatch) < 1e-9, 0.0, best_dispatch)


def solve_angles(case, model, dispatch):
    injections = np.zeros(len(model["non_slack"]), dtype=float)
    for retained, station in zip(dispatch, case["stations"]):
        injections[model["non_slack_index"][int(station["bus"])]] += (
            float(retained) / model["base_mva"]
        )
    return model["inverse_b"] @ injections


def build_report_from_dispatch(case, model, dispatch):
    theta = solve_angles(case, model, dispatch)
    cable_rows = []
    for cable in case["cables"]:
        f_bus = int(cable["from"])
        t_bus = int(cable["to"])
        theta_from = (
            0.0
            if f_bus == model["slack_id"]
            else theta[model["non_slack_index"][f_bus]]
        )
        theta_to = (
            0.0
            if t_bus == model["slack_id"]
            else theta[model["non_slack_index"][t_bus]]
        )
        flow_mw = model["base_mva"] * (theta_from - theta_to) / float(cable["x_pu"])
        cable_rows.append(
            {
                "id": cable["id"],
                "name": cable["name"],
                "from": f_bus,
                "to": t_bus,
                "kind": cable["kind"],
                "flow_MW": float(flow_mw),
                "limit_MW": float(cable["limit_MW"]),
                "loading_pct": abs(float(flow_mw)) / float(cable["limit_MW"]) * 100.0,
            }
        )

    cable_map = {row["id"]: row for row in cable_rows}

    station_plans = []
    total_available = 0.0
    total_retained = 0.0
    weighted_score = 0.0
    for retained, station in zip(dispatch, case["stations"]):
        available = float(station["available_MW"])
        curtailed = available - float(retained)
        total_available += available
        total_retained += float(retained)
        weighted_score += float(station["priority_weight"]) * curtailed
        station_plans.append(
            {
                "id": station["id"],
                "name": station["name"],
                "bus": int(station["bus"]),
                "available_MW": rounded(available),
                "retained_MW": rounded(retained),
                "curtailed_MW": rounded(curtailed),
                "priority_weight": rounded(station["priority_weight"]),
            }
        )

    key_cable_results = []
    for cable_id in case["report_cable_ids"]:
        row = cable_map[cable_id]
        key_cable_results.append(
            {
                "id": row["id"],
                "name": row["name"],
                "from": row["from"],
                "to": row["to"],
                "kind": row["kind"],
                "flow_MW": rounded(row["flow_MW"]),
                "limit_MW": rounded(row["limit_MW"]),
                "loading_pct": rounded(row["loading_pct"]),
            }
        )

    critical_cables = [
        {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "loading_pct": rounded(row["loading_pct"]),
        }
        for row in cable_rows
        if row["loading_pct"] + 1e-9 >= float(case["critical_threshold_pct"])
    ]
    critical_cables.sort(key=lambda item: (-item["loading_pct"], item["id"]))

    total_curtailment = total_available - total_retained
    optimization_score = (
        float(case["objective_total_curtailment_weight"]) * total_curtailment
        + weighted_score
    )

    return {
        "case_id": case["case_id"],
        "station_plans": station_plans,
        "key_cable_results": key_cable_results,
        "critical_cables": critical_cables,
        "totals": {
            "available_MW": rounded(total_available),
            "retained_MW": rounded(total_retained),
            "total_curtailment_MW": rounded(total_curtailment),
            "weighted_curtailment_score": rounded(weighted_score),
            "optimization_score": rounded(optimization_score),
        },
    }


@pytest.fixture(scope="module")
def case():
    with open(CASE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def model(case):
    return build_model(case)


@pytest.fixture(scope="module")
def reference(case, model):
    dispatch = enumerate_optimal_dispatch(case, model)
    return build_report_from_dispatch(case, model, dispatch)


def test_schema_and_order(case, report):
    assert set(report.keys()) == {
        "case_id",
        "station_plans",
        "key_cable_results",
        "critical_cables",
        "totals",
    }
    assert report["case_id"] == case["case_id"]

    assert [row["id"] for row in report["station_plans"]] == [
        row["id"] for row in case["stations"]
    ]
    for row in report["station_plans"]:
        assert set(row.keys()) == {
            "id",
            "name",
            "bus",
            "available_MW",
            "retained_MW",
            "curtailed_MW",
            "priority_weight",
        }

    assert [row["id"] for row in report["key_cable_results"]] == case["report_cable_ids"]
    for row in report["key_cable_results"]:
        assert set(row.keys()) == {
            "id",
            "name",
            "from",
            "to",
            "kind",
            "flow_MW",
            "limit_MW",
            "loading_pct",
        }

    for row in report["critical_cables"]:
        assert set(row.keys()) == {"id", "name", "kind", "loading_pct"}

    assert set(report["totals"].keys()) == {
        "available_MW",
        "retained_MW",
        "total_curtailment_MW",
        "weighted_curtailment_score",
        "optimization_score",
    }


def test_optimal_station_plan(report, reference):
    for actual, expected in zip(report["station_plans"], reference["station_plans"]):
        assert actual["id"] == expected["id"]
        assert actual["name"] == expected["name"]
        assert actual["bus"] == expected["bus"]
        for key in [
            "available_MW",
            "retained_MW",
            "curtailed_MW",
            "priority_weight",
        ]:
            assert actual[key] == pytest.approx(expected[key], abs=TOL)


def test_flow_consistency_and_limits(case, report, model):
    dispatch = np.array(
        [float(row["retained_MW"]) for row in report["station_plans"]], dtype=float
    )
    rebuilt = build_report_from_dispatch(case, model, dispatch)

    for actual, expected in zip(report["key_cable_results"], rebuilt["key_cable_results"]):
        assert actual["id"] == expected["id"]
        assert actual["name"] == expected["name"]
        assert actual["from"] == expected["from"]
        assert actual["to"] == expected["to"]
        assert actual["kind"] == expected["kind"]
        for key in ["flow_MW", "limit_MW", "loading_pct"]:
            assert actual[key] == pytest.approx(expected[key], abs=TOL)

    assert report["critical_cables"] == rebuilt["critical_cables"]

    for row in rebuilt["key_cable_results"]:
        assert abs(float(row["flow_MW"])) <= float(row["limit_MW"]) + TOL

    retained_sum = sum(float(row["retained_MW"]) for row in report["station_plans"])
    curtailed_sum = sum(float(row["curtailed_MW"]) for row in report["station_plans"])
    available_sum = sum(float(row["available_MW"]) for row in report["station_plans"])
    assert retained_sum + curtailed_sum == pytest.approx(available_sum, abs=TOL)


def test_totals_and_objective(report, reference):
    totals = report["totals"]
    expected = reference["totals"]
    for key in totals:
        assert totals[key] == pytest.approx(expected[key], abs=TOL)
