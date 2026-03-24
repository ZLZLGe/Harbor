import json
import os
from pathlib import Path

import pytest

TOL = 1e-2


def resolve_existing_path(*candidates):
    for candidate in candidates:
        path = Path(candidate)
        try:
            if path.exists():
                return str(path)
        except PermissionError:
            continue
    raise FileNotFoundError(f"None of these paths exist: {candidates}")


OUTPUT_FILE = resolve_existing_path(
    "/root/dispatch_impact.json",
    "dispatch_impact.json",
)
INPUT_FILE = resolve_existing_path(
    "/root/fleet_data.json",
    "environment/fleet_data.json",
)


def merit_order(generators):
    return sorted(
        generators,
        key=lambda gen: (-gen["energy_bid_dollars_per_mwh"], gen["generator_id"]),
    )


def solve_dispatch(generators, load_mw, reserve_requirement_mw):
    total_capacity = sum(gen["pmax_mw"] for gen in generators)
    total_headroom = total_capacity - load_mw
    assert total_headroom >= -1e-9, "Load exceeds total capacity"

    headroom = {gen["generator_id"]: 0.0 for gen in generators}
    remaining_reserve = reserve_requirement_mw

    for gen in merit_order(generators):
        headroom_cap = gen["pmax_mw"] - gen["pmin_mw"]
        reserve_cap = min(gen["reserve_cap_mw"], headroom_cap)
        allocate = min(remaining_reserve, reserve_cap)
        headroom[gen["generator_id"]] += allocate
        remaining_reserve -= allocate

    assert remaining_reserve <= 1e-9, "Reserve requirement infeasible"

    remaining_headroom = total_headroom - sum(headroom.values())
    assert remaining_headroom >= -1e-9, "Joint load/reserve problem infeasible"

    for gen in merit_order(generators):
        gen_id = gen["generator_id"]
        headroom_cap = gen["pmax_mw"] - gen["pmin_mw"]
        allocate = min(remaining_headroom, headroom_cap - headroom[gen_id])
        if allocate > 0:
            headroom[gen_id] += allocate
            remaining_headroom -= allocate

    assert remaining_headroom <= 1e-9, "Headroom assignment incomplete"

    reserve_awards = {gen["generator_id"]: 0.0 for gen in generators}
    remaining_reserve = reserve_requirement_mw
    for gen in merit_order(generators):
        gen_id = gen["generator_id"]
        feasible_reserve = min(gen["reserve_cap_mw"], headroom[gen_id])
        allocate = min(remaining_reserve, feasible_reserve)
        reserve_awards[gen_id] = allocate
        remaining_reserve -= allocate

    awards = []
    total_cost = 0.0
    for gen in generators:
        gen_id = gen["generator_id"]
        energy = gen["pmax_mw"] - headroom[gen_id]
        reserve = reserve_awards[gen_id]
        total_cost += gen["energy_bid_dollars_per_mwh"] * energy
        awards.append(
            {
                "generator_id": gen_id,
                "energy_mw": round(energy, 2),
                "reserve_mw": round(reserve, 2),
            }
        )

    return {
        "total_production_cost_dollars_per_hour": round(total_cost, 2),
        "generator_awards": awards,
    }


def scenario_result(generators, load_mw, reserve_requirement_mw):
    base = solve_dispatch(generators, load_mw, reserve_requirement_mw)
    load_plus_one = solve_dispatch(generators, load_mw + 1.0, reserve_requirement_mw)
    reserve_plus_one = solve_dispatch(generators, load_mw, reserve_requirement_mw + 1.0)
    return {
        "total_production_cost_dollars_per_hour": base[
            "total_production_cost_dollars_per_hour"
        ],
        "system_energy_price_dollars_per_mwh": round(
            load_plus_one["total_production_cost_dollars_per_hour"]
            - base["total_production_cost_dollars_per_hour"],
            2,
        ),
        "reserve_mcp_dollars_per_mw": round(
            reserve_plus_one["total_production_cost_dollars_per_hour"]
            - base["total_production_cost_dollars_per_hour"],
            2,
        ),
        "generator_awards": base["generator_awards"],
    }


def apply_counterfactual(data):
    generators = [dict(gen) for gen in data["generators"]]
    target = data["counterfactual"]["generator_id"]
    new_bid = data["counterfactual"]["new_energy_bid_dollars_per_mwh"]
    for gen in generators:
        if gen["generator_id"] == target:
            gen["energy_bid_dollars_per_mwh"] = new_bid
            return generators
    raise AssertionError("Counterfactual generator not found")


def impact_result(base_case, counterfactual):
    base_awards = {
        entry["generator_id"]: entry for entry in base_case["generator_awards"]
    }
    counter_awards = {
        entry["generator_id"]: entry for entry in counterfactual["generator_awards"]
    }
    rows = []
    for generator_id, base_entry in base_awards.items():
        counter_entry = counter_awards[generator_id]
        rows.append(
            {
                "generator_id": generator_id,
                "base_energy_mw": base_entry["energy_mw"],
                "counterfactual_energy_mw": counter_entry["energy_mw"],
                "energy_delta_mw": round(
                    counter_entry["energy_mw"] - base_entry["energy_mw"],
                    2,
                ),
                "base_reserve_mw": base_entry["reserve_mw"],
                "counterfactual_reserve_mw": counter_entry["reserve_mw"],
                "reserve_delta_mw": round(
                    counter_entry["reserve_mw"] - base_entry["reserve_mw"],
                    2,
                ),
            }
        )

    rows.sort(key=lambda entry: (-abs(entry["energy_delta_mw"]), entry["generator_id"]))
    return {
        "cost_change_dollars_per_hour": round(
            counterfactual["total_production_cost_dollars_per_hour"]
            - base_case["total_production_cost_dollars_per_hour"],
            2,
        ),
        "largest_redispatch_units": rows[:2],
    }


@pytest.fixture(scope="module")
def fleet_data():
    with open(INPUT_FILE, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def expected(fleet_data):
    base_case = scenario_result(
        fleet_data["generators"],
        fleet_data["load_mw"],
        fleet_data["reserve_requirement_mw"],
    )
    counterfactual = scenario_result(
        apply_counterfactual(fleet_data),
        fleet_data["load_mw"],
        fleet_data["reserve_requirement_mw"],
    )
    return {
        "base_case": base_case,
        "counterfactual": counterfactual,
        "impact_analysis": impact_result(base_case, counterfactual),
    }


def assert_close(actual, expected):
    assert actual == pytest.approx(expected, abs=TOL)


class TestSchema:
    def test_top_level_fields(self, report):
        assert set(report.keys()) == {"base_case", "counterfactual", "impact_analysis"}

    def test_scenario_fields(self, report, fleet_data):
        expected_generators = [g["generator_id"] for g in fleet_data["generators"]]
        for case_name in ["base_case", "counterfactual"]:
            case = report[case_name]
            assert set(case.keys()) == {
                "total_production_cost_dollars_per_hour",
                "system_energy_price_dollars_per_mwh",
                "reserve_mcp_dollars_per_mw",
                "generator_awards",
            }
            awards = case["generator_awards"]
            assert isinstance(awards, list)
            assert [entry["generator_id"] for entry in awards] == expected_generators
            for entry in awards:
                assert set(entry.keys()) == {"generator_id", "energy_mw", "reserve_mw"}

    def test_impact_fields(self, report):
        impact = report["impact_analysis"]
        assert set(impact.keys()) == {
            "cost_change_dollars_per_hour",
            "largest_redispatch_units",
        }
        assert len(impact["largest_redispatch_units"]) == 2


class TestExactValues:
    def test_base_case(self, report, expected):
        actual = report["base_case"]
        target = expected["base_case"]
        assert_close(
            actual["total_production_cost_dollars_per_hour"],
            target["total_production_cost_dollars_per_hour"],
        )
        assert_close(
            actual["system_energy_price_dollars_per_mwh"],
            target["system_energy_price_dollars_per_mwh"],
        )
        assert_close(
            actual["reserve_mcp_dollars_per_mw"],
            target["reserve_mcp_dollars_per_mw"],
        )
        assert actual["generator_awards"] == target["generator_awards"]

    def test_counterfactual(self, report, expected):
        actual = report["counterfactual"]
        target = expected["counterfactual"]
        assert_close(
            actual["total_production_cost_dollars_per_hour"],
            target["total_production_cost_dollars_per_hour"],
        )
        assert_close(
            actual["system_energy_price_dollars_per_mwh"],
            target["system_energy_price_dollars_per_mwh"],
        )
        assert_close(
            actual["reserve_mcp_dollars_per_mw"],
            target["reserve_mcp_dollars_per_mw"],
        )
        assert actual["generator_awards"] == target["generator_awards"]

    def test_impact_analysis(self, report, expected):
        actual = report["impact_analysis"]
        target = expected["impact_analysis"]
        assert_close(
            actual["cost_change_dollars_per_hour"],
            target["cost_change_dollars_per_hour"],
        )
        assert actual["largest_redispatch_units"] == target["largest_redispatch_units"]


class TestInternalConsistency:
    def test_cost_change_matches_cases(self, report):
        base_cost = report["base_case"]["total_production_cost_dollars_per_hour"]
        counter_cost = report["counterfactual"]["total_production_cost_dollars_per_hour"]
        assert_close(
            report["impact_analysis"]["cost_change_dollars_per_hour"],
            round(counter_cost - base_cost, 2),
        )

    def test_redispatch_rows_match_awards(self, report):
        base_awards = {
            row["generator_id"]: row for row in report["base_case"]["generator_awards"]
        }
        counter_awards = {
            row["generator_id"]: row
            for row in report["counterfactual"]["generator_awards"]
        }
        for row in report["impact_analysis"]["largest_redispatch_units"]:
            base_entry = base_awards[row["generator_id"]]
            counter_entry = counter_awards[row["generator_id"]]
            assert_close(row["base_energy_mw"], base_entry["energy_mw"])
            assert_close(
                row["counterfactual_energy_mw"],
                counter_entry["energy_mw"],
            )
            assert_close(
                row["energy_delta_mw"],
                round(counter_entry["energy_mw"] - base_entry["energy_mw"], 2),
            )
            assert_close(row["base_reserve_mw"], base_entry["reserve_mw"])
            assert_close(
                row["counterfactual_reserve_mw"],
                counter_entry["reserve_mw"],
            )
            assert_close(
                row["reserve_delta_mw"],
                round(counter_entry["reserve_mw"] - base_entry["reserve_mw"], 2),
            )
