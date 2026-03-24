#!/usr/bin/env python3
"""Tests for the pH dosing caustic cutoff task."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REPORT_PATH = ROOT_DIR / "dosing_interlock_audit.json"


def load_report() -> dict:
    with REPORT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def phase_data(report: dict, phase_name: str) -> list[dict]:
    return report["phases"][phase_name]["data"]


def expected_command(report: dict, measured_ph: float, raw_pct: float) -> tuple[float, bool, bool]:
    limit_ph = report["high_limit_ph"]
    pump_min = report["pump_limits_pct"]["min"]
    pump_max = report["pump_limits_pct"]["max"]
    if measured_ph >= limit_ph:
        return 0.0, True, False
    applied_pct = max(pump_min, min(pump_max, raw_pct))
    command_clamped = abs(applied_pct - raw_pct) > 1e-9
    return round(applied_pct, 4), False, command_clamped


def phase_expected_events(report: dict) -> list[tuple[str, float, float, float, float, str]]:
    expected = []
    for phase_name in ["trial_dose", "regulate"]:
        for sample in phase_data(report, phase_name):
            applied_pct, high_limit_triggered, command_clamped = expected_command(
                report, sample["pre_command_ph"], sample["raw_caustic_pct"]
            )
            if high_limit_triggered:
                expected.append(
                    (
                        phase_name,
                        sample["time_sec"],
                        sample["pre_command_ph"],
                        sample["raw_caustic_pct"],
                        applied_pct,
                        "high_ph_cutoff",
                    )
                )
            elif command_clamped:
                expected.append(
                    (
                        phase_name,
                        sample["time_sec"],
                        sample["pre_command_ph"],
                        sample["raw_caustic_pct"],
                        applied_pct,
                        "command_clamped_to_range",
                    )
                )
    return expected


def audit_expected_events(report: dict) -> list[tuple[str, float, float, float, float, str]]:
    expected = []
    for case_name in ["cutoff_probe", "clamp_probe"]:
        case = report["audit_cases"][case_name]
        applied_pct, high_limit_triggered, _ = expected_command(
            report, case["measured_ph"], case["raw_caustic_pct"]
        )
        event_type = "high_ph_cutoff" if high_limit_triggered else "command_clamped_to_range"
        expected.append(
            (
                case_name,
                0.0,
                case["measured_ph"],
                case["raw_caustic_pct"],
                applied_pct,
                event_type,
            )
        )
    return expected


def actual_events(report: dict) -> list[tuple[str, float, float, float, float, str]]:
    return [
        (
            event["phase"],
            event["time_sec"],
            event["measured_ph"],
            event["raw_caustic_pct"],
            event["applied_caustic_pct"],
            event["event_type"],
        )
        for event in report["event_log"]["events"]
    ]


class TestStructure:
    def test_report_exists(self):
        assert REPORT_PATH.exists(), "dosing_interlock_audit.json is missing"

    def test_top_level_fields(self):
        report = load_report()
        for field in [
            "report_version",
            "fermentor_id",
            "target_ph",
            "target_band",
            "high_limit_ph",
            "pump_limits_pct",
            "phases",
            "event_log",
            "audit_cases",
            "summary",
            "compliance",
        ]:
            assert field in report, f"missing top-level field: {field}"

        assert report["report_version"] == 1
        assert report["fermentor_id"] == "FERM-22"
        assert report["target_ph"] == 6.8
        assert report["target_band"] == {"low": 6.75, "high": 6.9}
        assert report["high_limit_ph"] == 7.2
        assert report["pump_limits_pct"] == {"min": 0.0, "max": 45.0}


class TestPhaseLogs:
    def test_phase_presence_and_monotonic_time(self):
        report = load_report()
        for phase_name in ["trial_dose", "regulate"]:
            samples = phase_data(report, phase_name)
            assert samples, f"{phase_name} data is empty"

            last_time = None
            for index, sample in enumerate(samples):
                for field in [
                    "time_sec",
                    "pre_command_ph",
                    "measured_ph",
                    "raw_caustic_pct",
                    "applied_caustic_pct",
                    "safety_checked",
                    "high_limit_triggered",
                    "command_clamped",
                ]:
                    assert field in sample, f"{phase_name}[{index}] missing {field}"

                assert sample["safety_checked"] is True
                assert 0.0 <= sample["applied_caustic_pct"] <= 45.0

                if last_time is not None:
                    assert sample["time_sec"] > last_time, f"{phase_name} timestamps are not strictly increasing"
                last_time = sample["time_sec"]

    def test_safety_logic_matches_reported_samples(self):
        report = load_report()
        for phase_name in ["trial_dose", "regulate"]:
            for index, sample in enumerate(phase_data(report, phase_name)):
                expected_applied, high_limit_triggered, command_clamped = expected_command(
                    report, sample["pre_command_ph"], sample["raw_caustic_pct"]
                )
                assert sample["applied_caustic_pct"] == expected_applied, \
                    f"{phase_name}[{index}] applied command does not match the safety logic"
                assert sample["high_limit_triggered"] is high_limit_triggered
                assert sample["command_clamped"] is command_clamped


class TestEvents:
    def test_event_log_matches_phase_and_audit_decisions(self):
        report = load_report()
        expected = phase_expected_events(report) + audit_expected_events(report)
        assert actual_events(report) == expected, "event_log.events does not match reconstructed decisions"

    def test_event_log_has_both_cutoff_and_clamp_entries(self):
        report = load_report()
        events = report["event_log"]["events"]
        event_types = {event["event_type"] for event in events}
        assert "high_ph_cutoff" in event_types
        assert "command_clamped_to_range" in event_types


class TestAuditCases:
    def test_cutoff_probe_forces_zero_output(self):
        report = load_report()
        probe = report["audit_cases"]["cutoff_probe"]
        assert probe["measured_ph"] == 7.24
        assert probe["raw_caustic_pct"] == 18.0
        assert probe["applied_caustic_pct"] == 0.0
        assert probe["high_limit_triggered"] is True
        assert probe["command_clamped"] is False
        assert probe["event_logged"] is True

    def test_clamp_probe_hits_output_limit_without_cutoff(self):
        report = load_report()
        probe = report["audit_cases"]["clamp_probe"]
        assert probe["measured_ph"] == 6.18
        assert probe["raw_caustic_pct"] == 58.0
        assert probe["applied_caustic_pct"] == 45.0
        assert probe["high_limit_triggered"] is False
        assert probe["command_clamped"] is True
        assert probe["event_logged"] is True


class TestPerformance:
    def test_trial_phase_contains_high_ph_cutoff_sample(self):
        report = load_report()
        cutoff_samples = [
            sample for sample in phase_data(report, "trial_dose")
            if sample["pre_command_ph"] >= report["high_limit_ph"]
        ]
        assert cutoff_samples, "trial_dose must include at least one cutoff sample"
        for sample in cutoff_samples:
            assert sample["applied_caustic_pct"] == 0.0

    def test_regulate_phase_finishes_in_target_band(self):
        report = load_report()
        last_sample = phase_data(report, "regulate")[-1]
        band_low = report["target_band"]["low"]
        band_high = report["target_band"]["high"]
        assert band_low <= last_sample["measured_ph"] <= band_high
        assert report["summary"]["final_in_target_band"] is True

    def test_tail_error_matches_summary(self):
        report = load_report()
        tail_count = report["summary"]["regulate_tail_samples"]
        samples = phase_data(report, "regulate")[-tail_count:]
        expected_mae = round(
            sum(abs(report["target_ph"] - sample["measured_ph"]) for sample in samples) / tail_count,
            4,
        )
        assert report["summary"]["regulate_tail_mean_abs_error"] == expected_mae
        assert expected_mae <= 0.08

    def test_limit_summary_matches_phase_data(self):
        report = load_report()
        all_samples = phase_data(report, "trial_dose") + phase_data(report, "regulate")
        cutoff_samples = [sample for sample in all_samples if sample["pre_command_ph"] >= report["high_limit_ph"]]
        expected_max_applied = max((sample["applied_caustic_pct"] for sample in cutoff_samples), default=0.0)

        assert report["summary"]["trial_peak_ph"] == max(sample["measured_ph"] for sample in phase_data(report, "trial_dose"))
        assert report["summary"]["regulate_final_ph"] == phase_data(report, "regulate")[-1]["measured_ph"]
        assert report["summary"]["samples_at_or_above_limit"] == len(cutoff_samples)
        assert report["summary"]["max_applied_command_when_at_or_above_limit_pct"] == expected_max_applied


class TestCompliance:
    def test_compliance_counts_match_event_log(self):
        report = load_report()
        events = report["event_log"]["events"]
        cutoff_count = sum(1 for event in events if event["event_type"] == "high_ph_cutoff")
        clamp_count = sum(1 for event in events if event["event_type"] == "command_clamped_to_range")

        assert report["compliance"]["high_ph_cutoff_respected"] is True
        assert report["compliance"]["command_clamp_respected"] is True
        assert report["compliance"]["logged_event_count"] == len(events)
        assert report["compliance"]["cutoff_event_count"] == cutoff_count
        assert report["compliance"]["clamp_event_count"] == clamp_count
