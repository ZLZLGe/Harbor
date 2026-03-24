#!/usr/bin/env python3
"""Tests for the tank fill overflow interlock task."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REPORT_PATH = ROOT_DIR / "fill_interlock_summary.json"


def load_report() -> dict:
    with REPORT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def phase_data(report: dict, phase_name: str) -> list[dict]:
    return report["phases"][phase_name]["data"]


def compute_contiguous_hold_sec(samples: list[dict], band_low: float, band_high: float) -> float:
    best = 0.0
    current = 0.0
    last_time = None

    for sample in samples:
        time_sec = sample["time_sec"]
        step = 0.0 if last_time is None else round(time_sec - last_time, 2)
        in_band = band_low <= sample["measured_level_pct"] <= band_high
        if in_band:
            current = step if last_time is None else current + step
            best = max(best, current)
        else:
            current = 0.0
        last_time = time_sec

    return round(best, 2)


def freeze_respected(samples: list[dict], high_level_pct: float, reopen_fill_pct: float) -> bool:
    frozen = False
    for sample in samples:
        if sample["pre_command_level_pct"] >= high_level_pct:
            frozen = True
        elif frozen and sample["pre_command_level_pct"] < reopen_fill_pct:
            frozen = False

        if frozen and sample["applied_inlet_pct"] != 0.0:
            return False
    return True


class TestStructure:
    def test_report_exists(self):
        assert REPORT_PATH.exists(), "fill_interlock_summary.json is missing"

    def test_top_level_fields(self):
        report = load_report()
        for field in [
            "report_version",
            "tank_id",
            "target_band_pct",
            "high_level_interlock_pct",
            "reopen_fill_pct",
            "phases",
            "safety_log",
            "summary",
            "safety_proof",
        ]:
            assert field in report, f"missing top-level field: {field}"

        assert report["report_version"] == 1
        assert report["tank_id"] == "TK-204"
        assert report["high_level_interlock_pct"] == 92.0
        assert report["reopen_fill_pct"] == 89.5


class TestPhaseLogs:
    def test_phases_are_non_empty(self):
        report = load_report()
        for phase_name in ["pulse_test", "auto_fill"]:
            assert phase_name in report["phases"], f"missing phase: {phase_name}"
            assert phase_data(report, phase_name), f"{phase_name} data is empty"

    def test_sample_shape_and_monotonic_time(self):
        report = load_report()
        for phase_name in ["pulse_test", "auto_fill"]:
            samples = phase_data(report, phase_name)
            last_time = None
            for index, sample in enumerate(samples):
                for field in [
                    "time_sec",
                    "pre_command_level_pct",
                    "measured_level_pct",
                    "requested_inlet_pct",
                    "applied_inlet_pct",
                    "high_level_checked",
                    "interlock_active",
                    "fill_frozen",
                ]:
                    assert field in sample, f"{phase_name}[{index}] missing {field}"

                assert sample["high_level_checked"] is True
                assert 0.0 <= sample["applied_inlet_pct"] <= 100.0

                if last_time is not None:
                    assert sample["time_sec"] > last_time, f"{phase_name} timestamps are not strictly increasing"
                last_time = sample["time_sec"]

    def test_commands_cut_off_at_or_above_interlock(self):
        report = load_report()
        high_level_pct = report["high_level_interlock_pct"]
        all_samples = phase_data(report, "pulse_test") + phase_data(report, "auto_fill")
        cutoff_samples = [sample for sample in all_samples if sample["pre_command_level_pct"] >= high_level_pct]

        assert cutoff_samples, "expected at least one high-level cutoff sample"
        for sample in cutoff_samples:
            assert sample["applied_inlet_pct"] == 0.0, "fill command was not cut off at the interlock"


class TestSafetyEvents:
    def test_logged_events_match_cutoff_samples(self):
        report = load_report()
        high_level_pct = report["high_level_interlock_pct"]
        all_samples = phase_data(report, "pulse_test") + phase_data(report, "auto_fill")
        events = report["safety_log"]["events"]

        assert isinstance(events, list) and events, "safety_log.events must contain at least one cutoff"

        cutoff_levels = {
            sample["pre_command_level_pct"]
            for sample in all_samples
            if sample["pre_command_level_pct"] >= high_level_pct and sample["applied_inlet_pct"] == 0.0
        }
        event_levels = {event["measured_level_pct"] for event in events}

        assert event_levels.issubset(cutoff_levels), "logged events do not match cutoff samples"
        for event in events:
            assert event["applied_inlet_pct"] == 0.0
            assert event["reason"] == "high_level_cutoff"

    def test_freeze_until_reopen(self):
        report = load_report()
        high_level_pct = report["high_level_interlock_pct"]
        reopen_fill_pct = report["reopen_fill_pct"]
        all_samples = phase_data(report, "pulse_test") + phase_data(report, "auto_fill")

        assert freeze_respected(all_samples, high_level_pct, reopen_fill_pct), \
            "fill freeze was not maintained until the reopen threshold"


class TestPerformance:
    def test_hold_requirement(self):
        report = load_report()
        band_low = report["target_band_pct"]["low"]
        band_high = report["target_band_pct"]["high"]
        auto_samples = phase_data(report, "auto_fill")
        hold_sec = compute_contiguous_hold_sec(auto_samples, band_low, band_high)

        assert hold_sec >= 120.0, f"contiguous hold duration {hold_sec}s is below 120s"
        assert abs(report["summary"]["contiguous_hold_sec"] - hold_sec) < 1e-6
        assert report["summary"]["target_band_reached"] is True

    def test_no_overflow_and_summary_consistency(self):
        report = load_report()
        all_samples = phase_data(report, "pulse_test") + phase_data(report, "auto_fill")
        max_level = max(sample["measured_level_pct"] for sample in all_samples)

        assert max_level < 100.0, f"measured level {max_level}% reached overflow"
        assert abs(report["summary"]["max_level_pct"] - max_level) < 1e-6
        assert report["summary"]["never_overflowed"] is True
        assert abs(report["safety_proof"]["overflow_margin_pct"] - (100.0 - max_level)) < 1e-6


class TestSafetyProof:
    def test_safety_proof_matches_data(self):
        report = load_report()
        high_level_pct = report["high_level_interlock_pct"]
        reopen_fill_pct = report["reopen_fill_pct"]
        all_samples = phase_data(report, "pulse_test") + phase_data(report, "auto_fill")

        cutoff_samples = [sample for sample in all_samples if sample["pre_command_level_pct"] >= high_level_pct]
        expected_max_applied = max((sample["applied_inlet_pct"] for sample in cutoff_samples), default=0.0)

        proof = report["safety_proof"]
        assert proof["all_samples_checked"] is True
        assert proof["samples_at_or_above_interlock"] == len(cutoff_samples)
        assert proof["max_applied_inlet_at_or_above_interlock_pct"] == expected_max_applied
        assert proof["freeze_respected_until_reopen"] is True
        assert freeze_respected(all_samples, high_level_pct, reopen_fill_pct)
