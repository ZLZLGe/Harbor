#!/usr/bin/env python3
"""Tests for the battery-pack preheat safety report."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REPORT_PATH = ROOT_DIR / "battery_safety_report.json"


def load_report() -> dict:
    with REPORT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def max_cell(sample: dict) -> float:
    return max(sample["cell_temps_c"])


def compute_latch_and_first_ready(report: dict) -> tuple[list[float], float | None]:
    trip_temp = report["cell_trip_temp_c"]
    reset_temp = report["cell_reset_temp_c"]
    charge_min = report["charge_window_c"]["min"]
    charge_max = report["charge_window_c"]["max"]

    interlock_times = []
    interlock_active = False
    first_ready = None

    for sample in report["trajectory"]:
        sample_max = max_cell(sample)
        if sample_max >= trip_temp:
            if not interlock_active:
                interlock_times.append(sample["time_sec"])
            interlock_active = True
        elif interlock_active and sample_max < reset_temp:
            interlock_active = False

        charge_enable = (
            (not interlock_active)
            and charge_min <= sample["module_temp_c"] <= charge_max
            and sample_max < reset_temp
        )
        if charge_enable and first_ready is None:
            first_ready = sample["time_sec"]

    return interlock_times, first_ready


class TestStructure:
    def test_report_exists(self):
        assert REPORT_PATH.exists(), "battery_safety_report.json is missing"

    def test_top_level_fields(self):
        report = load_report()
        for field in [
            "report_version",
            "pack_id",
            "charge_window_c",
            "cell_trip_temp_c",
            "cell_reset_temp_c",
            "trajectory",
            "interlock_events",
            "summary",
            "final_decision",
        ]:
            assert field in report, f"missing top-level field: {field}"

        assert report["report_version"] == 1
        assert report["pack_id"] == "BP-17"
        assert report["charge_window_c"] == {"min": 17.0, "max": 23.0}
        assert report["cell_trip_temp_c"] == 32.0
        assert report["cell_reset_temp_c"] == 30.5


class TestTrajectory:
    def test_trajectory_non_empty_and_monotonic(self):
        report = load_report()
        trajectory = report["trajectory"]
        assert trajectory, "trajectory is empty"

        last_time = None
        for index, sample in enumerate(trajectory):
            for field in [
                "time_sec",
                "module_temp_c",
                "cell_temps_c",
                "requested_heater_pct",
                "applied_heater_pct",
                "interlock_active",
                "charge_enable",
            ]:
                assert field in sample, f"trajectory[{index}] missing {field}"

            assert isinstance(sample["cell_temps_c"], list) and len(sample["cell_temps_c"]) == 4
            assert 0.0 <= sample["applied_heater_pct"] <= 100.0

            if last_time is not None:
                assert sample["time_sec"] > last_time, "trajectory timestamps are not strictly increasing"
            last_time = sample["time_sec"]

    def test_cutoff_and_latch_behavior(self):
        report = load_report()
        trip_temp = report["cell_trip_temp_c"]
        reset_temp = report["cell_reset_temp_c"]

        interlock_active = False
        saw_cutoff = False

        for index, sample in enumerate(report["trajectory"]):
            sample_max = max_cell(sample)
            if sample_max >= trip_temp:
                interlock_active = True
                saw_cutoff = True
            elif interlock_active and sample_max < reset_temp:
                interlock_active = False

            if sample_max >= trip_temp:
                assert sample["applied_heater_pct"] == 0.0, \
                    f"trajectory[{index}] did not force heater off at the trip temperature"
                assert sample["charge_enable"] is False, \
                    f"trajectory[{index}] left charge_enable true at the trip temperature"

            if interlock_active:
                assert sample["applied_heater_pct"] == 0.0, \
                    f"trajectory[{index}] applied heat while the cutoff latch should be active"
                assert sample["charge_enable"] is False, \
                    f"trajectory[{index}] enabled charging before the cells cooled below reset"

        assert saw_cutoff, "expected at least one overtemperature cutoff"


class TestEventsAndSummary:
    def test_event_log_matches_reconstructed_triggers(self):
        report = load_report()
        expected_times, _ = compute_latch_and_first_ready(report)
        event_times = [event["time_sec"] for event in report["interlock_events"]]

        assert event_times == expected_times, "interlock_events do not match the reconstructed trigger times"
        assert event_times, "interlock_events must contain at least one cutoff"

        for event in report["interlock_events"]:
            assert event["applied_heater_pct"] == 0.0
            assert event["charge_enable_after_cutoff"] is False
            assert event["reason"] == "cell_overtemp_cutoff"
            assert 1 <= event["triggering_cell_index"] <= 4

    def test_summary_matches_trajectory(self):
        report = load_report()
        expected_times, first_ready = compute_latch_and_first_ready(report)
        last_sample = report["trajectory"][-1]
        summary = report["summary"]

        assert summary["trajectory_samples"] == len(report["trajectory"])
        assert summary["interlock_trigger_times_sec"] == expected_times
        assert summary["interlock_trigger_count"] == len(expected_times)
        assert summary["first_chargeable_time_sec"] == first_ready
        assert summary["final_module_temp_c"] == last_sample["module_temp_c"]
        assert summary["final_max_cell_temp_c"] == max_cell(last_sample)
        assert summary["final_charge_enable"] == last_sample["charge_enable"]
        assert summary["heater_forced_off_while_interlocked"] is True


class TestFinalDecision:
    def test_final_decision_matches_last_sample(self):
        report = load_report()
        last_sample = report["trajectory"][-1]
        final_decision = report["final_decision"]

        assert final_decision["charge_enable"] == last_sample["charge_enable"]
        assert final_decision["module_temp_c"] == last_sample["module_temp_c"]
        assert final_decision["max_cell_temp_c"] == max_cell(last_sample)

    def test_scenario_finishes_charge_ready(self):
        report = load_report()
        final_decision = report["final_decision"]
        last_sample = report["trajectory"][-1]

        assert final_decision["charge_enable"] is True, "this scenario should recover into a charge-ready state"
        assert final_decision["reason"] == "module_in_window_and_cells_below_reset"
        assert 17.0 <= last_sample["module_temp_c"] <= 23.0
        assert max_cell(last_sample) < report["cell_reset_temp_c"]
        assert report["summary"]["first_chargeable_time_sec"] is not None
