import json
import os

import pytest

OUTPUT_FILE = "/root/steam_dispatch_report.json"
INPUT_FILE = "/root/steam_station_snapshot.json"
TOL = 1e-4


def validate_blocks(asset, step):
    total_block_steam = 0
    for block in asset["fuel_cost_blocks"]:
        steam = int(block["steam_tph"])
        assert steam % step == 0
        total_block_steam += steam
    assert total_block_steam == int(asset["steam_max_tph"])


def build_energy_costs(asset, step):
    validate_blocks(asset, step)
    costs = {0: 0.0}
    running_cost = 0.0
    scheduled_steam = 0

    for block in asset["fuel_cost_blocks"]:
        block_steps = int(block["steam_tph"]) // step
        marginal_cost = float(block["marginal_cost_dollars_per_tph"])
        for _ in range(block_steps):
            scheduled_steam += step
            running_cost += step * marginal_cost
            costs[scheduled_steam] = running_cost

    assert scheduled_steam == int(asset["steam_max_tph"])
    return costs


def solve_snapshot(snapshot):
    step = int(snapshot["dispatch_step_tph"])
    demand = int(snapshot["steam_demand_tph"])
    reserve_requirement = int(snapshot["hot_reserve_requirement_tph"])
    assets = snapshot["assets"]

    dp = {(0, 0): 0.0}
    parents = []

    for asset in assets:
        min_steam = int(asset["steam_min_tph"])
        max_steam = int(asset["steam_max_tph"])
        reserve_cap = int(asset["hot_reserve_max_tph"])
        reserve_cost = float(asset["hot_reserve_cost_dollars_per_tph"])

        assert min_steam % step == 0
        assert max_steam % step == 0
        assert reserve_cap % step == 0

        energy_costs = build_energy_costs(asset, step)
        options = []
        for steam in range(min_steam, max_steam + step, step):
            usable_reserve = min(reserve_cap, max_steam - steam)
            base_cost = energy_costs[steam]
            for reserve in range(0, usable_reserve + step, step):
                options.append((steam, reserve, base_cost + reserve * reserve_cost))

        next_dp = {}
        parent = {}
        for (steam_total, reserve_total), total_cost in dp.items():
            for steam, reserve, option_cost in options:
                new_steam = steam_total + steam
                if new_steam > demand:
                    continue
                new_reserve = min(reserve_requirement, reserve_total + reserve)
                state = (new_steam, new_reserve)
                candidate_cost = total_cost + option_cost
                if candidate_cost < next_dp.get(state, float("inf")) - 1e-9:
                    next_dp[state] = candidate_cost
                    parent[state] = ((steam_total, reserve_total), (steam, reserve))

        dp = next_dp
        parents.append(parent)

    terminal_state = (demand, reserve_requirement)
    assert terminal_state in dp

    decisions = []
    state = terminal_state
    for parent in reversed(parents):
        previous_state, choice = parent[state]
        decisions.append(choice)
        state = previous_state
    decisions.reverse()

    asset_dispatch = []
    technology_totals = {}
    fully_committed_assets = []

    for asset, (steam, reserve) in zip(assets, decisions):
        spare_headroom = int(asset["steam_max_tph"]) - steam - reserve
        asset_dispatch.append(
            {
                "asset_id": asset["asset_id"],
                "asset_type": asset["asset_type"],
                "steam_output_tph": float(steam),
                "hot_reserve_tph": float(reserve),
                "spare_headroom_tph": float(spare_headroom),
            }
        )
        bucket = technology_totals.setdefault(
            asset["asset_type"],
            {"steam_output_tph": 0.0, "hot_reserve_tph": 0.0, "spare_headroom_tph": 0.0},
        )
        bucket["steam_output_tph"] += steam
        bucket["hot_reserve_tph"] += reserve
        bucket["spare_headroom_tph"] += spare_headroom
        if spare_headroom == 0:
            fully_committed_assets.append(asset["asset_id"])

    return {
        "asset_dispatch": asset_dispatch,
        "summary": {
            "steam_demand_tph": float(demand),
            "steam_scheduled_tph": float(sum(item["steam_output_tph"] for item in asset_dispatch)),
            "hot_reserve_requirement_tph": float(reserve_requirement),
            "hot_reserve_scheduled_tph": float(sum(item["hot_reserve_tph"] for item in asset_dispatch)),
            "total_fuel_cost_dollars_per_hour": float(dp[terminal_state]),
            "average_fuel_cost_dollars_per_ton": float(dp[terminal_state] / demand),
        },
        "technology_totals": [
            {
                "asset_type": asset_type,
                "steam_output_tph": float(values["steam_output_tph"]),
                "hot_reserve_tph": float(values["hot_reserve_tph"]),
                "spare_headroom_tph": float(values["spare_headroom_tph"]),
            }
            for asset_type, values in sorted(technology_totals.items())
        ],
        "fully_committed_assets": sorted(fully_committed_assets),
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
        assert report["station_id"]
        assert "asset_dispatch" in report
        assert "summary" in report
        assert "technology_totals" in report
        assert "fully_committed_assets" in report

    def test_asset_dispatch_schema(self, report, snapshot):
        assert isinstance(report["asset_dispatch"], list)
        assert len(report["asset_dispatch"]) == len(snapshot["assets"])
        for item in report["asset_dispatch"]:
            assert set(item.keys()) == {
                "asset_id",
                "asset_type",
                "steam_output_tph",
                "hot_reserve_tph",
                "spare_headroom_tph",
            }

    def test_summary_schema(self, report):
        assert set(report["summary"].keys()) == {
            "steam_demand_tph",
            "steam_scheduled_tph",
            "hot_reserve_requirement_tph",
            "hot_reserve_scheduled_tph",
            "total_fuel_cost_dollars_per_hour",
            "average_fuel_cost_dollars_per_ton",
        }

    def test_technology_totals_schema(self, report):
        assert isinstance(report["technology_totals"], list)
        for item in report["technology_totals"]:
            assert set(item.keys()) == {
                "asset_type",
                "steam_output_tph",
                "hot_reserve_tph",
                "spare_headroom_tph",
            }


class TestFeasibility:
    def test_asset_order_matches_input(self, report, snapshot):
        report_ids = [item["asset_id"] for item in report["asset_dispatch"]]
        input_ids = [asset["asset_id"] for asset in snapshot["assets"]]
        assert report_ids == input_ids

    def test_dispatch_respects_bounds_and_step(self, report, snapshot):
        step = snapshot["dispatch_step_tph"]
        for item, asset in zip(report["asset_dispatch"], snapshot["assets"]):
            steam = item["steam_output_tph"]
            reserve = item["hot_reserve_tph"]
            headroom = item["spare_headroom_tph"]
            assert steam >= asset["steam_min_tph"] - TOL
            assert steam <= asset["steam_max_tph"] + TOL
            assert reserve >= -TOL
            assert reserve <= asset["hot_reserve_max_tph"] + TOL
            assert steam + reserve <= asset["steam_max_tph"] + TOL
            assert headroom == pytest.approx(asset["steam_max_tph"] - steam - reserve, abs=TOL)
            assert (steam / step) == pytest.approx(round(steam / step), abs=TOL)
            assert (reserve / step) == pytest.approx(round(reserve / step), abs=TOL)

    def test_summary_totals_are_consistent(self, report, snapshot):
        steam_sum = sum(item["steam_output_tph"] for item in report["asset_dispatch"])
        reserve_sum = sum(item["hot_reserve_tph"] for item in report["asset_dispatch"])
        headroom_sum = sum(item["spare_headroom_tph"] for item in report["asset_dispatch"])

        assert report["summary"]["steam_demand_tph"] == pytest.approx(snapshot["steam_demand_tph"], abs=TOL)
        assert report["summary"]["steam_scheduled_tph"] == pytest.approx(steam_sum, abs=TOL)
        assert steam_sum == pytest.approx(snapshot["steam_demand_tph"], abs=TOL)
        assert report["summary"]["hot_reserve_requirement_tph"] == pytest.approx(
            snapshot["hot_reserve_requirement_tph"], abs=TOL
        )
        assert report["summary"]["hot_reserve_scheduled_tph"] == pytest.approx(reserve_sum, abs=TOL)
        assert reserve_sum >= snapshot["hot_reserve_requirement_tph"] - TOL

        technology_headroom = sum(item["spare_headroom_tph"] for item in report["technology_totals"])
        assert technology_headroom == pytest.approx(headroom_sum, abs=TOL)

    def test_technology_totals_and_fully_committed(self, report):
        technology_order = [item["asset_type"] for item in report["technology_totals"]]
        assert technology_order == sorted(technology_order)
        assert report["fully_committed_assets"] == sorted(report["fully_committed_assets"])

        fully_committed = {
            item["asset_id"]
            for item in report["asset_dispatch"]
            if item["spare_headroom_tph"] == pytest.approx(0.0, abs=TOL)
        }
        assert report["fully_committed_assets"] == sorted(fully_committed)


class TestOptimality:
    def test_optimal_asset_dispatch(self, report, optimal):
        for reported, expected in zip(report["asset_dispatch"], optimal["asset_dispatch"]):
            assert reported["asset_id"] == expected["asset_id"]
            assert reported["asset_type"] == expected["asset_type"]
            assert reported["steam_output_tph"] == pytest.approx(expected["steam_output_tph"], abs=TOL)
            assert reported["hot_reserve_tph"] == pytest.approx(expected["hot_reserve_tph"], abs=TOL)
            assert reported["spare_headroom_tph"] == pytest.approx(expected["spare_headroom_tph"], abs=TOL)

    def test_optimal_summary(self, report, optimal):
        for key, value in optimal["summary"].items():
            assert report["summary"][key] == pytest.approx(value, abs=TOL)

    def test_optimal_technology_totals(self, report, optimal):
        assert len(report["technology_totals"]) == len(optimal["technology_totals"])
        for reported, expected in zip(report["technology_totals"], optimal["technology_totals"]):
            assert reported["asset_type"] == expected["asset_type"]
            assert reported["steam_output_tph"] == pytest.approx(expected["steam_output_tph"], abs=TOL)
            assert reported["hot_reserve_tph"] == pytest.approx(expected["hot_reserve_tph"], abs=TOL)
            assert reported["spare_headroom_tph"] == pytest.approx(expected["spare_headroom_tph"], abs=TOL)

    def test_optimal_fully_committed_assets(self, report, optimal):
        assert report["fully_committed_assets"] == optimal["fully_committed_assets"]
