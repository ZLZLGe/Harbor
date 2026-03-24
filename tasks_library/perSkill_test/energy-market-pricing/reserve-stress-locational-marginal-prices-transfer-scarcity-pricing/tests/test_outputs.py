import json
import os
from pathlib import Path

import cvxpy as cp
import numpy as np
import pytest

OUTPUT_FILE = Path("/root/scarcity_pricing_report.json")
NETWORK_FILE = Path("/root/reserve_pocket_network.json")
EVENT_FILE = Path("/root/reserve_stress_event.json")

VALUE_TOL = 0.05


@pytest.fixture(scope="module")
def report():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with NETWORK_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def event():
    with EVENT_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def build_branch_susceptance_matrix(branches, bus_num_to_idx):
    n_bus = len(bus_num_to_idx)
    b_matrix = np.zeros((n_bus, n_bus))
    branch_susceptances = []
    for br in branches:
        f = bus_num_to_idx[int(br[0])]
        t = bus_num_to_idx[int(br[1])]
        x = float(br[3])
        if x != 0:
            susceptance = 1.0 / x
            b_matrix[f, f] += susceptance
            b_matrix[t, t] += susceptance
            b_matrix[f, t] -= susceptance
            b_matrix[t, f] -= susceptance
            branch_susceptances.append(susceptance)
        else:
            branch_susceptances.append(0.0)
    return b_matrix, branch_susceptances


def solve_reference_case(network, reserve_requirement, reserve_capacity, binding_threshold_pct, scenario_id):
    base_mva = float(network["baseMVA"])
    buses = np.array(network["bus"], dtype=float)
    gens = np.array(network["gen"], dtype=float)
    branches = np.array(network["branch"], dtype=float)
    gencost = np.array(network["gencost"], dtype=float)

    n_bus = len(buses)
    n_gen = len(gens)
    bus_num_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
    slack_idx = next(i for i in range(n_bus) if int(buses[i, 1]) == 3)
    gen_bus = [bus_num_to_idx[int(g[0])] for g in gens]

    b_matrix, branch_susceptances = build_branch_susceptance_matrix(branches, bus_num_to_idx)

    pg = cp.Variable(n_gen)
    rg = cp.Variable(n_gen)
    theta = cp.Variable(n_bus)

    objective = 0
    for i in range(n_gen):
        c2, c1, c0 = gencost[i, 4], gencost[i, 5], gencost[i, 6]
        pg_mw = pg[i] * base_mva
        objective += c2 * cp.square(pg_mw) + c1 * pg_mw + c0

    constraints = []
    balance_constraints = []
    for i in range(n_bus):
        generation_at_bus = sum(pg[g] for g in range(n_gen) if gen_bus[g] == i)
        demand_pu = buses[i, 2] / base_mva
        balance = generation_at_bus - demand_pu == b_matrix[i, :] @ theta
        balance_constraints.append(balance)
        constraints.append(balance)

    for i in range(n_gen):
        constraints.append(pg[i] >= gens[i, 9] / base_mva)
        constraints.append(pg[i] <= gens[i, 8] / base_mva)

    constraints.append(rg >= 0)
    for i in range(n_gen):
        constraints.append(rg[i] <= reserve_capacity[i])
        constraints.append(pg[i] * base_mva + rg[i] <= gens[i, 8])

    reserve_constraint = cp.sum(rg) >= reserve_requirement
    constraints.append(reserve_constraint)
    constraints.append(theta[slack_idx] == 0)

    for k, br in enumerate(branches):
        f = bus_num_to_idx[int(br[0])]
        t = bus_num_to_idx[int(br[1])]
        rate = float(br[5])
        susceptance = branch_susceptances[k]
        if susceptance == 0 or rate <= 0:
            continue
        flow = susceptance * (theta[f] - theta[t]) * base_mva
        constraints.append(flow <= rate)
        constraints.append(flow >= -rate)

    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(solver=cp.CLARABEL)
    assert problem.status == "optimal", f"{scenario_id} solve status: {problem.status}"

    theta_value = theta.value
    lmp_by_bus = []
    for i in range(n_bus):
        lmp_by_bus.append(
            {
                "bus": int(buses[i, 0]),
                "lmp_dollars_per_MWh": round(float(balance_constraints[i].dual_value) * base_mva, 2),
            }
        )

    binding_lines = []
    for k, br in enumerate(branches):
        f = bus_num_to_idx[int(br[0])]
        t = bus_num_to_idx[int(br[1])]
        rate = float(br[5])
        susceptance = branch_susceptances[k]
        if susceptance == 0 or rate <= 0:
            continue
        flow_mw = float(susceptance * (theta_value[f] - theta_value[t]) * base_mva)
        loading_pct = abs(flow_mw) / rate * 100.0
        if loading_pct >= binding_threshold_pct:
            binding_lines.append(
                {
                    "from": int(br[0]),
                    "to": int(br[1]),
                    "flow_MW": round(flow_mw, 2),
                    "limit_MW": round(rate, 2),
                    "loading_pct": round(loading_pct, 2),
                }
            )

    binding_lines.sort(key=lambda item: (item["from"], item["to"]))
    lmp_by_bus.sort(key=lambda item: item["bus"])

    reserve_mcp = float(reserve_constraint.dual_value) if reserve_constraint.dual_value is not None else 0.0
    return {
        "scenario_id": scenario_id,
        "reserve_requirement_MW": round(float(reserve_requirement), 2),
        "total_cost_dollars_per_hour": round(float(problem.value), 2),
        "reserve_mcp_dollars_per_MWh": round(reserve_mcp, 2),
        "lmp_by_bus": lmp_by_bus,
        "binding_lines": binding_lines,
    }


def make_lmp_map(case_result):
    return {entry["bus"]: entry["lmp_dollars_per_MWh"] for entry in case_result["lmp_by_bus"]}


@pytest.fixture(scope="module")
def reference_solution(network, event):
    base_case = solve_reference_case(
        network=network,
        reserve_requirement=float(network["reserve_requirement"]),
        reserve_capacity=np.array(network["reserve_capacity"], dtype=float),
        binding_threshold_pct=float(event["binding_threshold_pct"]),
        scenario_id="base_case",
    )

    stress_capacity = np.array(network["reserve_capacity"], dtype=float)
    bus_to_gen = {int(gen[0]): idx for idx, gen in enumerate(network["gen"])}
    for adjustment in event["reserve_capacity_adjustments"]:
        stress_capacity[bus_to_gen[int(adjustment["generator_bus"])]] = float(
            adjustment["stress_reserve_capacity_MW"]
        )

    stress_case = solve_reference_case(
        network=network,
        reserve_requirement=float(event["stress_reserve_requirement_MW"]),
        reserve_capacity=stress_capacity,
        binding_threshold_pct=float(event["binding_threshold_pct"]),
        scenario_id=event["stress_scenario_id"],
    )

    base_lmp = make_lmp_map(base_case)
    stress_lmp = make_lmp_map(stress_case)

    bus_to_region = {}
    regional_price_impacts = []
    for region in event["regions"]:
        region_changes = [stress_lmp[bus] - base_lmp[bus] for bus in region["buses"]]
        for bus in region["buses"]:
            bus_to_region[bus] = region["region_id"]
        regional_price_impacts.append(
            {
                "region_id": region["region_id"],
                "region_name": region["region_name"],
                "buses": region["buses"],
                "average_base_lmp_dollars_per_MWh": round(
                    sum(base_lmp[bus] for bus in region["buses"]) / len(region["buses"]), 2
                ),
                "average_stress_lmp_dollars_per_MWh": round(
                    sum(stress_lmp[bus] for bus in region["buses"]) / len(region["buses"]), 2
                ),
                "average_lmp_change_dollars_per_MWh": round(sum(region_changes) / len(region_changes), 2),
                "max_lmp_change_dollars_per_MWh": round(max(region_changes), 2),
                "affected_bus_count": sum(1 for change in region_changes if change > 0),
            }
        )

    bus_changes = []
    for bus in sorted(base_lmp):
        bus_changes.append(
            {
                "bus": bus,
                "region_id": bus_to_region[bus],
                "base_lmp_dollars_per_MWh": round(base_lmp[bus], 2),
                "stress_lmp_dollars_per_MWh": round(stress_lmp[bus], 2),
                "delta_dollars_per_MWh": round(stress_lmp[bus] - base_lmp[bus], 2),
            }
        )
    bus_changes.sort(key=lambda item: (-item["delta_dollars_per_MWh"], item["bus"]))

    most_affected_region = min(
        regional_price_impacts,
        key=lambda item: (-item["average_lmp_change_dollars_per_MWh"], item["region_id"]),
    )

    thresholds = event["energy_price_transmission_rule"]
    reserve_mcp_increase = round(
        stress_case["reserve_mcp_dollars_per_MWh"] - base_case["reserve_mcp_dollars_per_MWh"], 2
    )

    return {
        "base_case": base_case,
        "reserve_stress_case": stress_case,
        "scarcity_transfer_assessment": {
            "system_cost_increase_dollars_per_hour": round(
                stress_case["total_cost_dollars_per_hour"] - base_case["total_cost_dollars_per_hour"], 2
            ),
            "reserve_mcp_increase_dollars_per_MWh": reserve_mcp_increase,
            "largest_lmp_increases": bus_changes[: int(event["report_top_n_buses"])],
            "regional_price_impacts": regional_price_impacts,
            "most_affected_region_id": most_affected_region["region_id"],
            "scarcity_pricing_transmitted_to_energy": (
                reserve_mcp_increase
                >= thresholds["reserve_mcp_increase_threshold_dollars_per_MWh"]
                and most_affected_region["average_lmp_change_dollars_per_MWh"]
                >= thresholds["regional_average_lmp_increase_threshold_dollars_per_MWh"]
            ),
            "assessment_basis": {
                "reserve_mcp_increase_threshold_dollars_per_MWh": round(
                    float(thresholds["reserve_mcp_increase_threshold_dollars_per_MWh"]), 2
                ),
                "regional_average_lmp_increase_threshold_dollars_per_MWh": round(
                    float(thresholds["regional_average_lmp_increase_threshold_dollars_per_MWh"]), 2
                ),
            },
        },
    }


class TestSchema:
    def test_top_level_structure(self, report, event, network):
        assert set(report.keys()) == {
            "base_case",
            "reserve_stress_case",
            "scarcity_transfer_assessment",
        }

        for case_name in ["base_case", "reserve_stress_case"]:
            case = report[case_name]
            assert "scenario_id" in case
            assert "reserve_requirement_MW" in case
            assert "total_cost_dollars_per_hour" in case
            assert "reserve_mcp_dollars_per_MWh" in case
            assert "lmp_by_bus" in case
            assert "binding_lines" in case
            assert len(case["lmp_by_bus"]) == len(network["bus"])

        assessment = report["scarcity_transfer_assessment"]
        assert "system_cost_increase_dollars_per_hour" in assessment
        assert "reserve_mcp_increase_dollars_per_MWh" in assessment
        assert "largest_lmp_increases" in assessment
        assert len(assessment["largest_lmp_increases"]) == int(event["report_top_n_buses"])
        assert "regional_price_impacts" in assessment
        assert len(assessment["regional_price_impacts"]) == len(event["regions"])
        assert "most_affected_region_id" in assessment
        assert isinstance(assessment["scarcity_pricing_transmitted_to_energy"], bool)


class TestReferenceMatch:
    def test_scenario_outputs_match_reference(self, report, reference_solution):
        for case_name in ["base_case", "reserve_stress_case"]:
            actual = report[case_name]
            expected = reference_solution[case_name]
            assert actual["scenario_id"] == expected["scenario_id"]
            assert actual["reserve_requirement_MW"] == pytest.approx(
                expected["reserve_requirement_MW"], abs=VALUE_TOL
            )
            assert actual["total_cost_dollars_per_hour"] == pytest.approx(
                expected["total_cost_dollars_per_hour"], abs=VALUE_TOL
            )
            assert actual["reserve_mcp_dollars_per_MWh"] == pytest.approx(
                expected["reserve_mcp_dollars_per_MWh"], abs=VALUE_TOL
            )
            assert actual["binding_lines"] == expected["binding_lines"]
            assert actual["lmp_by_bus"] == expected["lmp_by_bus"]

    def test_assessment_matches_reference(self, report, reference_solution):
        actual = report["scarcity_transfer_assessment"]
        expected = reference_solution["scarcity_transfer_assessment"]
        assert actual["system_cost_increase_dollars_per_hour"] == pytest.approx(
            expected["system_cost_increase_dollars_per_hour"], abs=VALUE_TOL
        )
        assert actual["reserve_mcp_increase_dollars_per_MWh"] == pytest.approx(
            expected["reserve_mcp_increase_dollars_per_MWh"], abs=VALUE_TOL
        )
        assert actual["largest_lmp_increases"] == expected["largest_lmp_increases"]
        assert actual["regional_price_impacts"] == expected["regional_price_impacts"]
        assert actual["most_affected_region_id"] == expected["most_affected_region_id"]
        assert actual["scarcity_pricing_transmitted_to_energy"] == expected["scarcity_pricing_transmitted_to_energy"]
        assert actual["assessment_basis"] == expected["assessment_basis"]


class TestConsistency:
    def test_cost_and_reserve_deltas(self, report):
        assessment = report["scarcity_transfer_assessment"]
        base_case = report["base_case"]
        stress_case = report["reserve_stress_case"]

        assert assessment["system_cost_increase_dollars_per_hour"] == pytest.approx(
            stress_case["total_cost_dollars_per_hour"] - base_case["total_cost_dollars_per_hour"],
            abs=VALUE_TOL,
        )
        assert assessment["reserve_mcp_increase_dollars_per_MWh"] == pytest.approx(
            stress_case["reserve_mcp_dollars_per_MWh"] - base_case["reserve_mcp_dollars_per_MWh"],
            abs=VALUE_TOL,
        )

    def test_ranked_bus_deltas_are_correct(self, report):
        base_lmp = make_lmp_map(report["base_case"])
        stress_lmp = make_lmp_map(report["reserve_stress_case"])
        previous_delta = None
        previous_bus = None

        for entry in report["scarcity_transfer_assessment"]["largest_lmp_increases"]:
            expected_delta = round(stress_lmp[entry["bus"]] - base_lmp[entry["bus"]], 2)
            assert entry["delta_dollars_per_MWh"] == pytest.approx(expected_delta, abs=VALUE_TOL)
            if previous_delta is not None:
                assert entry["delta_dollars_per_MWh"] <= previous_delta + VALUE_TOL
                if entry["delta_dollars_per_MWh"] == pytest.approx(previous_delta, abs=VALUE_TOL):
                    assert entry["bus"] >= previous_bus
            previous_delta = entry["delta_dollars_per_MWh"]
            previous_bus = entry["bus"]

    def test_transmission_flag_is_backed_by_thresholds(self, report):
        assessment = report["scarcity_transfer_assessment"]
        basis = assessment["assessment_basis"]
        most_affected = next(
            region
            for region in assessment["regional_price_impacts"]
            if region["region_id"] == assessment["most_affected_region_id"]
        )
        expected = (
            assessment["reserve_mcp_increase_dollars_per_MWh"]
            >= basis["reserve_mcp_increase_threshold_dollars_per_MWh"]
            and most_affected["average_lmp_change_dollars_per_MWh"]
            >= basis["regional_average_lmp_increase_threshold_dollars_per_MWh"]
        )
        assert assessment["scarcity_pricing_transmitted_to_energy"] == expected
