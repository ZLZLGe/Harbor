import json
import os

import pytest
from scipy.optimize import linprog

OUTPUT_FILE = "/root/balancing_market_report.json"
INPUT_FILE = "/root/balancing_market_snapshot.json"
TOL = 1e-4


def solve_snapshot(snapshot):
    units = snapshot["units"]
    load = snapshot["load_MW"]
    reserve_requirement = snapshot["reserve_requirement_MW"]

    block_meta = []
    reserve_indices = {}
    objective = []
    bounds = []

    for unit_idx, unit in enumerate(units):
        block_total = 0.0
        for block in unit["energy_blocks"]:
            objective.append(float(block["price"]))
            bounds.append((0.0, float(block["mw"])))
            block_meta.append((unit_idx, float(block["mw"])))
            block_total += float(block["mw"])
        assert block_total == pytest.approx(float(unit["p_max_MW"]), abs=TOL)

    for unit_idx, unit in enumerate(units):
        reserve_indices[unit_idx] = len(objective)
        objective.append(float(unit["reserve_offer_dollars_per_MW"]))
        bounds.append((0.0, float(unit["reserve_max_MW"])))

    n_vars = len(objective)

    def unit_block_indices(target_unit_idx):
        return [idx for idx, (unit_idx, _width) in enumerate(block_meta) if unit_idx == target_unit_idx]

    a_eq = []
    b_eq = []
    energy_balance = [0.0] * n_vars
    for idx in range(len(block_meta)):
        energy_balance[idx] = 1.0
    a_eq.append(energy_balance)
    b_eq.append(load)

    a_ub = []
    b_ub = []

    reserve_requirement_row = [0.0] * n_vars
    for unit_idx in range(len(units)):
        reserve_requirement_row[reserve_indices[unit_idx]] = -1.0
    a_ub.append(reserve_requirement_row)
    b_ub.append(-reserve_requirement)

    for unit_idx, unit in enumerate(units):
        block_indices = unit_block_indices(unit_idx)

        min_row = [0.0] * n_vars
        for idx in block_indices:
            min_row[idx] = -1.0
        a_ub.append(min_row)
        b_ub.append(-float(unit["p_min_MW"]))

        coupling_row = [0.0] * n_vars
        for idx in block_indices:
            coupling_row[idx] = 1.0
        coupling_row[reserve_indices[unit_idx]] = 1.0
        a_ub.append(coupling_row)
        b_ub.append(float(unit["p_max_MW"]))

    result = linprog(
        c=objective,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    assert result.success, result.message

    dispatch = []
    tight_units = []
    uncommitted_capacity = 0.0

    for unit_idx, unit in enumerate(units):
        energy = sum(result.x[idx] for idx in unit_block_indices(unit_idx))
        reserve = result.x[reserve_indices[unit_idx]]
        headroom = float(unit["p_max_MW"]) - energy - reserve
        if abs(headroom) <= TOL:
            headroom = 0.0

        dispatch.append(
            {
                "unit_id": unit["unit_id"],
                "energy_MW": energy,
                "reserve_MW": reserve,
                "headroom_MW": headroom,
                "p_max_MW": float(unit["p_max_MW"]),
                "p_min_MW": float(unit["p_min_MW"]),
                "reserve_max_MW": float(unit["reserve_max_MW"]),
            }
        )
        uncommitted_capacity += max(headroom, 0.0)

        if headroom == 0.0:
            tight_units.append(
                {
                    "unit_id": unit["unit_id"],
                    "binding_reason": "energy_plus_reserve_hits_pmax",
                    "headroom_MW": 0.0,
                }
            )

    tight_units.sort(key=lambda item: item["unit_id"])

    return {
        "dispatch": dispatch,
        "tight_units": tight_units,
        "uncommitted_capacity_MW": uncommitted_capacity,
        "cost": result.fun,
        "load_MW": load,
        "reserve_requirement_MW": reserve_requirement,
        "energy_cleared_MW": sum(item["energy_MW"] for item in dispatch),
        "reserve_cleared_MW": sum(item["reserve_MW"] for item in dispatch),
    }


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"Missing {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def snapshot():
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def optimal(snapshot):
    return solve_snapshot(snapshot)


class TestSchema:
    def test_top_level_fields(self, report):
        assert report["market_id"]
        assert "unit_dispatch" in report
        assert "totals" in report
        assert "marginal_tight_units" in report
        assert "uncommitted_capacity_MW" in report

    def test_unit_dispatch_schema(self, report, snapshot):
        assert isinstance(report["unit_dispatch"], list)
        assert len(report["unit_dispatch"]) == len(snapshot["units"])
        for item in report["unit_dispatch"]:
            assert set(item.keys()) == {
                "unit_id",
                "energy_MW",
                "reserve_MW",
                "headroom_MW",
                "p_max_MW",
            }

    def test_totals_schema(self, report):
        assert set(report["totals"].keys()) == {
            "load_MW",
            "energy_cleared_MW",
            "reserve_requirement_MW",
            "reserve_cleared_MW",
            "total_cost_dollars_per_hour",
        }


class TestFeasibility:
    def test_unit_order_matches_input(self, report, snapshot):
        report_ids = [item["unit_id"] for item in report["unit_dispatch"]]
        input_ids = [unit["unit_id"] for unit in snapshot["units"]]
        assert report_ids == input_ids

    def test_dispatch_respects_bounds(self, report, snapshot):
        for item, unit in zip(report["unit_dispatch"], snapshot["units"]):
            energy = item["energy_MW"]
            reserve = item["reserve_MW"]
            headroom = item["headroom_MW"]
            assert energy >= unit["p_min_MW"] - TOL
            assert energy <= unit["p_max_MW"] + TOL
            assert reserve >= -TOL
            assert reserve <= unit["reserve_max_MW"] + TOL
            assert energy + reserve <= unit["p_max_MW"] + TOL
            assert headroom == pytest.approx(unit["p_max_MW"] - energy - reserve, abs=TOL)

    def test_report_totals_are_consistent(self, report, snapshot):
        energy_sum = sum(item["energy_MW"] for item in report["unit_dispatch"])
        reserve_sum = sum(item["reserve_MW"] for item in report["unit_dispatch"])
        headroom_sum = sum(item["headroom_MW"] for item in report["unit_dispatch"])

        assert report["totals"]["load_MW"] == pytest.approx(snapshot["load_MW"], abs=TOL)
        assert report["totals"]["reserve_requirement_MW"] == pytest.approx(
            snapshot["reserve_requirement_MW"], abs=TOL
        )
        assert report["totals"]["energy_cleared_MW"] == pytest.approx(energy_sum, abs=TOL)
        assert report["totals"]["reserve_cleared_MW"] == pytest.approx(reserve_sum, abs=TOL)
        assert energy_sum == pytest.approx(snapshot["load_MW"], abs=TOL)
        assert reserve_sum >= snapshot["reserve_requirement_MW"] - TOL
        assert report["uncommitted_capacity_MW"] == pytest.approx(headroom_sum, abs=TOL)

    def test_tight_units_are_sorted_and_binding(self, report):
        tight_units = report["marginal_tight_units"]
        ids = [item["unit_id"] for item in tight_units]
        assert ids == sorted(ids)
        for item in tight_units:
            assert item["binding_reason"] == "energy_plus_reserve_hits_pmax"
            assert item["headroom_MW"] == pytest.approx(0.0, abs=TOL)


class TestOptimality:
    def test_optimal_dispatch(self, report, optimal):
        for reported, expected in zip(report["unit_dispatch"], optimal["dispatch"]):
            assert reported["unit_id"] == expected["unit_id"]
            assert reported["energy_MW"] == pytest.approx(expected["energy_MW"], abs=TOL)
            assert reported["reserve_MW"] == pytest.approx(expected["reserve_MW"], abs=TOL)
            assert reported["headroom_MW"] == pytest.approx(expected["headroom_MW"], abs=TOL)
            assert reported["p_max_MW"] == pytest.approx(expected["p_max_MW"], abs=TOL)

    def test_optimal_totals_and_cost(self, report, optimal):
        totals = report["totals"]
        assert totals["load_MW"] == pytest.approx(optimal["load_MW"], abs=TOL)
        assert totals["energy_cleared_MW"] == pytest.approx(optimal["energy_cleared_MW"], abs=TOL)
        assert totals["reserve_requirement_MW"] == pytest.approx(
            optimal["reserve_requirement_MW"], abs=TOL
        )
        assert totals["reserve_cleared_MW"] == pytest.approx(optimal["reserve_cleared_MW"], abs=TOL)
        assert totals["total_cost_dollars_per_hour"] == pytest.approx(optimal["cost"], abs=TOL)
        assert report["uncommitted_capacity_MW"] == pytest.approx(
            optimal["uncommitted_capacity_MW"], abs=TOL
        )

    def test_optimal_tight_units(self, report, optimal):
        reported = report["marginal_tight_units"]
        expected = optimal["tight_units"]
        assert len(reported) == len(expected)
        for reported_item, expected_item in zip(reported, expected):
            assert reported_item["unit_id"] == expected_item["unit_id"]
            assert reported_item["binding_reason"] == expected_item["binding_reason"]
            assert reported_item["headroom_MW"] == pytest.approx(expected_item["headroom_MW"], abs=TOL)
