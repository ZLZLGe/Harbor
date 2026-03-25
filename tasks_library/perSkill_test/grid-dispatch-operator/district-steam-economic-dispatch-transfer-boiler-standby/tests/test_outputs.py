import csv
import os
import tomllib

import pytest

INPUT_PROFILE = "/root/station_request.toml"
INPUT_FLEET = "/root/boiler_fleet.csv"
OUTPUT_FILE = "/root/steam_commitment.toml"
EPS = 1e-6


def read_inputs():
    with open(INPUT_PROFILE, "rb") as f:
        profile = tomllib.load(f)

    boilers = []
    with open(INPUT_FLEET, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            boilers.append(
                {
                    "boiler_id": row["boiler_id"],
                    "boiler_class": row["boiler_class"],
                    "min_steam_klb_per_hr": float(row["min_steam_klb_per_hr"]),
                    "max_steam_klb_per_hr": float(row["max_steam_klb_per_hr"]),
                    "standby_cap_klb_per_hr": float(row["standby_cap_klb_per_hr"]),
                    "incremental_heat_rate_mmbtu_per_klb": float(row["incremental_heat_rate_mmbtu_per_klb"]),
                    "standby_cost_dollars_per_klb": float(row["standby_cost_dollars_per_klb"]),
                }
            )

    return profile, boilers


def read_output():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, "rb") as f:
        return tomllib.load(f)


def enumerate_options(boiler, step, fuel_price):
    headroom_steps = int(round((boiler["max_steam_klb_per_hr"] - boiler["min_steam_klb_per_hr"]) / step))
    standby_cap_steps = int(round(boiler["standby_cap_klb_per_hr"] / step))

    for extra_steps in range(headroom_steps + 1):
        max_standby_steps = min(standby_cap_steps, headroom_steps - extra_steps)
        for standby_steps in range(max_standby_steps + 1):
            extra_steam = extra_steps * step
            standby = standby_steps * step
            cost = (
                extra_steam * boiler["incremental_heat_rate_mmbtu_per_klb"] * fuel_price
                + standby * boiler["standby_cost_dollars_per_klb"]
            )
            yield extra_steps, standby_steps, cost


def optimal_total_cost(profile, boilers):
    step = float(profile["dispatch_step_klb_per_hr"])
    fuel_price = float(profile["fuel_price_dollars_per_mmbtu"])
    base_steam = sum(boiler["min_steam_klb_per_hr"] for boiler in boilers)
    base_fuel_cost = sum(
        boiler["min_steam_klb_per_hr"] * boiler["incremental_heat_rate_mmbtu_per_klb"] * fuel_price
        for boiler in boilers
    )
    steam_target_steps = int(round((float(profile["steam_demand_klb_per_hr"]) - base_steam) / step))
    standby_target_steps = int(round(float(profile["standby_requirement_klb_per_hr"]) / step))

    states = {(0, 0): 0.0}
    for boiler in boilers:
        next_states = {}
        for (steam_steps, standby_steps), cost_so_far in states.items():
            for extra_steps, reserve_steps, add_cost in enumerate_options(boiler, step, fuel_price):
                new_steam_steps = steam_steps + extra_steps
                new_standby_steps = standby_steps + reserve_steps
                if new_steam_steps > steam_target_steps or new_standby_steps > standby_target_steps:
                    continue

                new_cost = cost_so_far + add_cost
                current = next_states.get((new_steam_steps, new_standby_steps))
                if current is None or new_cost < current - 1e-9:
                    next_states[(new_steam_steps, new_standby_steps)] = new_cost
        states = next_states

    return base_fuel_cost + states[(steam_target_steps, standby_target_steps)]


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def report():
    return read_output()


def test_schema(inputs, report):
    profile, boilers = inputs

    assert report["station_name"] == profile["station_name"]
    assert report["interval_start"] == profile["interval_start"]
    assert isinstance(report["boiler_commitment"], list)
    assert len(report["boiler_commitment"]) == len(boilers)
    assert "totals" in report

    expected_fields = {
        "boiler_id",
        "boiler_class",
        "steam_klb_per_hr",
        "standby_klb_per_hr",
        "idle_headroom_klb_per_hr",
        "fuel_cost_dollars_per_hour",
        "standby_cost_dollars_per_hour",
    }
    for entry in report["boiler_commitment"]:
        assert expected_fields.issubset(entry.keys())

    totals_fields = {
        "steam_demand_klb_per_hr",
        "steam_dispatched_klb_per_hr",
        "standby_requirement_klb_per_hr",
        "standby_allocated_klb_per_hr",
        "total_fuel_cost_dollars_per_hour",
        "total_standby_cost_dollars_per_hour",
        "total_operating_cost_dollars_per_hour",
        "remaining_standby_margin_klb_per_hr",
    }
    assert totals_fields.issubset(report["totals"].keys())


def test_order_and_identity(inputs, report):
    _, boilers = inputs
    expected_ids = [boiler["boiler_id"] for boiler in boilers]
    expected_classes = [boiler["boiler_class"] for boiler in boilers]

    reported_ids = [entry["boiler_id"] for entry in report["boiler_commitment"]]
    reported_classes = [entry["boiler_class"] for entry in report["boiler_commitment"]]

    assert reported_ids == expected_ids
    assert reported_classes == expected_classes


def test_feasibility_and_accounting(inputs, report):
    profile, boilers = inputs
    boiler_map = {boiler["boiler_id"]: boiler for boiler in boilers}
    step = float(profile["dispatch_step_klb_per_hr"])

    total_steam = 0.0
    total_standby = 0.0
    total_fuel_cost = 0.0
    total_standby_cost = 0.0
    total_margin = 0.0

    for entry in report["boiler_commitment"]:
        boiler = boiler_map[entry["boiler_id"]]
        steam = float(entry["steam_klb_per_hr"])
        standby = float(entry["standby_klb_per_hr"])
        margin = float(entry["idle_headroom_klb_per_hr"])
        fuel_cost = float(entry["fuel_cost_dollars_per_hour"])
        standby_cost = float(entry["standby_cost_dollars_per_hour"])

        assert boiler["min_steam_klb_per_hr"] - EPS <= steam <= boiler["max_steam_klb_per_hr"] + EPS
        assert -EPS <= standby <= boiler["standby_cap_klb_per_hr"] + EPS
        assert steam + standby <= boiler["max_steam_klb_per_hr"] + EPS

        steam_steps = round(steam / step)
        standby_steps = round(standby / step)
        assert steam == pytest.approx(steam_steps * step, abs=1e-6)
        assert standby == pytest.approx(standby_steps * step, abs=1e-6)

        expected_margin = boiler["max_steam_klb_per_hr"] - steam - standby
        expected_fuel_cost = steam * boiler["incremental_heat_rate_mmbtu_per_klb"] * float(profile["fuel_price_dollars_per_mmbtu"])
        expected_standby_cost = standby * boiler["standby_cost_dollars_per_klb"]

        assert margin == pytest.approx(expected_margin, abs=1e-6)
        assert fuel_cost == pytest.approx(expected_fuel_cost, abs=1e-6)
        assert standby_cost == pytest.approx(expected_standby_cost, abs=1e-6)

        total_steam += steam
        total_standby += standby
        total_fuel_cost += fuel_cost
        total_standby_cost += standby_cost
        total_margin += margin

    totals = report["totals"]
    assert total_steam == pytest.approx(float(profile["steam_demand_klb_per_hr"]), abs=1e-6)
    assert total_standby == pytest.approx(float(profile["standby_requirement_klb_per_hr"]), abs=1e-6)
    assert totals["steam_demand_klb_per_hr"] == pytest.approx(float(profile["steam_demand_klb_per_hr"]), abs=1e-6)
    assert totals["steam_dispatched_klb_per_hr"] == pytest.approx(total_steam, abs=1e-6)
    assert totals["standby_requirement_klb_per_hr"] == pytest.approx(float(profile["standby_requirement_klb_per_hr"]), abs=1e-6)
    assert totals["standby_allocated_klb_per_hr"] == pytest.approx(total_standby, abs=1e-6)
    assert totals["total_fuel_cost_dollars_per_hour"] == pytest.approx(total_fuel_cost, abs=1e-6)
    assert totals["total_standby_cost_dollars_per_hour"] == pytest.approx(total_standby_cost, abs=1e-6)
    assert totals["total_operating_cost_dollars_per_hour"] == pytest.approx(total_fuel_cost + total_standby_cost, abs=1e-6)
    assert totals["remaining_standby_margin_klb_per_hr"] == pytest.approx(total_margin, abs=1e-6)


def test_total_operating_cost_is_optimal(inputs, report):
    profile, boilers = inputs
    reference_cost = optimal_total_cost(profile, boilers)
    assert report["totals"]["total_operating_cost_dollars_per_hour"] == pytest.approx(reference_cost, abs=1e-6)
