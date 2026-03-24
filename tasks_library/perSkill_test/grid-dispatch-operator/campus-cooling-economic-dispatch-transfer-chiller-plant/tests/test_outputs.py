import json
import os

import pytest

OUTPUT_FILE = "/root/cooling_dispatch_summary.json"
INPUT_FILE = "/root/campus_cooling_snapshot.json"
TOL = 1e-4


def round4(value):
    return round(float(value), 4)


def solve_energy_dispatch(snapshot):
    chillers = snapshot["chillers"]
    target_load = float(snapshot["cooling_load_RT"])

    def clipped_output(lambda_value, chiller):
        quadratic = float(chiller["quadratic_power_kW_per_RT2"])
        linear = float(chiller["linear_power_kW_per_RT"])
        lower = float(chiller["cooling_min_RT"])
        upper = float(chiller["cooling_max_RT"])
        target = (lambda_value - linear) / (2.0 * quadratic)
        return min(upper, max(lower, target))

    low = min(
        float(chiller["linear_power_kW_per_RT"])
        + 2.0 * float(chiller["quadratic_power_kW_per_RT2"]) * float(chiller["cooling_min_RT"])
        for chiller in chillers
    ) - 10.0
    high = max(
        float(chiller["linear_power_kW_per_RT"])
        + 2.0 * float(chiller["quadratic_power_kW_per_RT2"]) * float(chiller["cooling_max_RT"])
        for chiller in chillers
    ) + 10.0

    for _ in range(200):
        midpoint = (low + high) / 2.0
        scheduled = sum(clipped_output(midpoint, chiller) for chiller in chillers)
        if scheduled < target_load:
            low = midpoint
        else:
            high = midpoint

    outputs = [clipped_output((low + high) / 2.0, chiller) for chiller in chillers]
    correction = target_load - sum(outputs)
    adjustable = [
        idx
        for idx, (output, chiller) in enumerate(zip(outputs, chillers))
        if float(chiller["cooling_min_RT"]) + 1e-7 < output < float(chiller["cooling_max_RT"]) - 1e-7
    ]
    if adjustable:
        share = correction / len(adjustable)
        for idx in adjustable:
            outputs[idx] += share
    return outputs


def allocate_reserve(snapshot, outputs):
    chillers = snapshot["chillers"]
    remaining = float(snapshot["spinning_reserve_requirement_RT"])
    reserves = [0.0] * len(chillers)
    reserve_stack_order = []

    order = sorted(
        range(len(chillers)),
        key=lambda idx: (int(chillers[idx]["reserve_priority"]), idx),
    )

    for idx in order:
        chiller = chillers[idx]
        headroom = float(chiller["cooling_max_RT"]) - outputs[idx]
        available = min(float(chiller["reserve_max_RT"]), max(0.0, headroom))
        assigned = min(available, remaining)
        reserves[idx] = assigned
        if assigned > 1e-7:
            reserve_stack_order.append(chiller["chiller_id"])
        remaining -= assigned
        if remaining <= 1e-7:
            break

    assert remaining <= 1e-7, "Reserve requirement is infeasible"
    return reserves, reserve_stack_order


def solve_snapshot(snapshot):
    outputs = solve_energy_dispatch(snapshot)
    reserves, reserve_stack_order = allocate_reserve(snapshot, outputs)
    price = float(snapshot["electricity_price_dollars_per_kWh"])

    chiller_dispatch = []
    plant_rollup = {}
    total_power = 0.0
    total_reserve = 0.0
    remaining_margin = 0.0

    for chiller, output, reserve in zip(snapshot["chillers"], outputs, reserves):
        power_draw = (
            float(chiller["no_load_power_kW"])
            + float(chiller["linear_power_kW_per_RT"]) * output
            + float(chiller["quadratic_power_kW_per_RT2"]) * output * output
        )
        unused_capacity = float(chiller["cooling_max_RT"]) - output - reserve
        total_power += power_draw
        total_reserve += reserve
        remaining_margin += unused_capacity

        chiller_dispatch.append(
            {
                "chiller_id": chiller["chiller_id"],
                "plant": chiller["plant"],
                "cooling_output_RT": round4(output),
                "spinning_reserve_RT": round4(reserve),
                "power_draw_kW": round4(power_draw),
                "available_capacity_RT": round4(chiller["cooling_max_RT"]),
                "unused_capacity_RT": round4(unused_capacity),
            }
        )

        bucket = plant_rollup.setdefault(
            chiller["plant"],
            {"cooling_output_RT": 0.0, "spinning_reserve_RT": 0.0, "unused_capacity_RT": 0.0},
        )
        bucket["cooling_output_RT"] += output
        bucket["spinning_reserve_RT"] += reserve
        bucket["unused_capacity_RT"] += unused_capacity

    return {
        "campus_id": snapshot["campus_id"],
        "operating_interval": snapshot["operating_interval"],
        "chiller_dispatch": chiller_dispatch,
        "summary": {
            "cooling_load_RT": round4(snapshot["cooling_load_RT"]),
            "scheduled_cooling_RT": round4(sum(outputs)),
            "spinning_reserve_requirement_RT": round4(snapshot["spinning_reserve_requirement_RT"]),
            "scheduled_spinning_reserve_RT": round4(total_reserve),
            "total_power_kW": round4(total_power),
            "total_electricity_cost_dollars_per_hour": round4(total_power * price),
            "remaining_margin_RT": round4(remaining_margin),
        },
        "plant_rollup": [
            {
                "plant": plant,
                "cooling_output_RT": round4(values["cooling_output_RT"]),
                "spinning_reserve_RT": round4(values["spinning_reserve_RT"]),
                "unused_capacity_RT": round4(values["unused_capacity_RT"]),
            }
            for plant, values in sorted(plant_rollup.items())
        ],
        "reserve_stack_order": reserve_stack_order,
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
def expected(snapshot):
    return solve_snapshot(snapshot)


class TestSchema:
    def test_top_level_fields(self, report):
        assert set(report.keys()) == {
            "campus_id",
            "operating_interval",
            "chiller_dispatch",
            "summary",
            "plant_rollup",
            "reserve_stack_order",
        }

    def test_chiller_dispatch_schema(self, report, snapshot):
        assert isinstance(report["chiller_dispatch"], list)
        assert len(report["chiller_dispatch"]) == len(snapshot["chillers"])
        for item in report["chiller_dispatch"]:
            assert set(item.keys()) == {
                "chiller_id",
                "plant",
                "cooling_output_RT",
                "spinning_reserve_RT",
                "power_draw_kW",
                "available_capacity_RT",
                "unused_capacity_RT",
            }

    def test_summary_schema(self, report):
        assert set(report["summary"].keys()) == {
            "cooling_load_RT",
            "scheduled_cooling_RT",
            "spinning_reserve_requirement_RT",
            "scheduled_spinning_reserve_RT",
            "total_power_kW",
            "total_electricity_cost_dollars_per_hour",
            "remaining_margin_RT",
        }

    def test_plant_rollup_schema(self, report):
        assert isinstance(report["plant_rollup"], list)
        for item in report["plant_rollup"]:
            assert set(item.keys()) == {
                "plant",
                "cooling_output_RT",
                "spinning_reserve_RT",
                "unused_capacity_RT",
            }


class TestFeasibility:
    def test_chiller_order_matches_input(self, report, snapshot):
        assert [item["chiller_id"] for item in report["chiller_dispatch"]] == [
            chiller["chiller_id"] for chiller in snapshot["chillers"]
        ]

    def test_dispatch_respects_bounds(self, report, snapshot):
        for item, chiller in zip(report["chiller_dispatch"], snapshot["chillers"]):
            output = item["cooling_output_RT"]
            reserve = item["spinning_reserve_RT"]
            available = item["available_capacity_RT"]
            unused = item["unused_capacity_RT"]

            assert item["plant"] == chiller["plant"]
            assert available == pytest.approx(chiller["cooling_max_RT"], abs=TOL)
            assert output >= chiller["cooling_min_RT"] - TOL
            assert output <= chiller["cooling_max_RT"] + TOL
            assert reserve >= -TOL
            assert reserve <= chiller["reserve_max_RT"] + TOL
            assert output + reserve <= chiller["cooling_max_RT"] + TOL
            assert unused == pytest.approx(chiller["cooling_max_RT"] - output - reserve, abs=TOL)

    def test_summary_consistency(self, report, snapshot):
        cooling_sum = sum(item["cooling_output_RT"] for item in report["chiller_dispatch"])
        reserve_sum = sum(item["spinning_reserve_RT"] for item in report["chiller_dispatch"])
        power_sum = sum(item["power_draw_kW"] for item in report["chiller_dispatch"])
        unused_sum = sum(item["unused_capacity_RT"] for item in report["chiller_dispatch"])

        assert report["summary"]["cooling_load_RT"] == pytest.approx(snapshot["cooling_load_RT"], abs=TOL)
        assert report["summary"]["scheduled_cooling_RT"] == pytest.approx(cooling_sum, abs=TOL)
        assert cooling_sum == pytest.approx(snapshot["cooling_load_RT"], abs=TOL)
        assert report["summary"]["spinning_reserve_requirement_RT"] == pytest.approx(
            snapshot["spinning_reserve_requirement_RT"], abs=TOL
        )
        assert report["summary"]["scheduled_spinning_reserve_RT"] == pytest.approx(reserve_sum, abs=TOL)
        assert reserve_sum >= snapshot["spinning_reserve_requirement_RT"] - TOL
        assert report["summary"]["total_power_kW"] == pytest.approx(power_sum, abs=TOL)
        assert report["summary"]["total_electricity_cost_dollars_per_hour"] == pytest.approx(
            power_sum * snapshot["electricity_price_dollars_per_kWh"], abs=TOL
        )
        assert report["summary"]["remaining_margin_RT"] == pytest.approx(unused_sum, abs=TOL)

    def test_plant_rollup_and_stack_order(self, report):
        plant_names = [item["plant"] for item in report["plant_rollup"]]
        assert plant_names == sorted(plant_names)
        positive_reserve = {
            item["chiller_id"]
            for item in report["chiller_dispatch"]
            if item["spinning_reserve_RT"] > TOL
        }
        assert len(report["reserve_stack_order"]) == len(set(report["reserve_stack_order"]))
        assert set(report["reserve_stack_order"]) == positive_reserve


class TestOptimality:
    def test_expected_dispatch(self, report, expected):
        for actual, target in zip(report["chiller_dispatch"], expected["chiller_dispatch"]):
            assert actual["chiller_id"] == target["chiller_id"]
            assert actual["plant"] == target["plant"]
            assert actual["cooling_output_RT"] == pytest.approx(target["cooling_output_RT"], abs=TOL)
            assert actual["spinning_reserve_RT"] == pytest.approx(target["spinning_reserve_RT"], abs=TOL)
            assert actual["power_draw_kW"] == pytest.approx(target["power_draw_kW"], abs=TOL)
            assert actual["available_capacity_RT"] == pytest.approx(target["available_capacity_RT"], abs=TOL)
            assert actual["unused_capacity_RT"] == pytest.approx(target["unused_capacity_RT"], abs=TOL)

    def test_expected_summary(self, report, expected):
        for key, value in expected["summary"].items():
            assert report["summary"][key] == pytest.approx(value, abs=TOL)

    def test_expected_plant_rollup(self, report, expected):
        assert len(report["plant_rollup"]) == len(expected["plant_rollup"])
        for actual, target in zip(report["plant_rollup"], expected["plant_rollup"]):
            assert actual["plant"] == target["plant"]
            assert actual["cooling_output_RT"] == pytest.approx(target["cooling_output_RT"], abs=TOL)
            assert actual["spinning_reserve_RT"] == pytest.approx(target["spinning_reserve_RT"], abs=TOL)
            assert actual["unused_capacity_RT"] == pytest.approx(target["unused_capacity_RT"], abs=TOL)

    def test_expected_reserve_stack_order(self, report, expected):
        assert report["reserve_stack_order"] == expected["reserve_stack_order"]
