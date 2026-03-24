#!/usr/bin/env python3
"""Tests for the air-handler startup safety report."""

import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REPORT_PATH = ROOT_DIR / "startup_safety_report.json"


def load_report():
    with open(REPORT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_phase_data(report, phase_name):
    return report["phases"][phase_name]["data"]


def compute_contiguous_hold_duration(samples, target_temp_c):
    if not samples:
        return 0.0

    best = 0.0
    current = 0.0
    last_time = None

    for sample in samples:
        time_sec = sample["time_sec"]
        step = 0.0 if last_time is None else round(time_sec - last_time, 2)
        if sample["measured_temp_c"] >= target_temp_c:
            current = step if last_time is None else current + step
            best = max(best, current)
        else:
            current = 0.0
        last_time = time_sec

    return round(best, 2)


class TestStructure:
    def test_report_exists(self):
        assert REPORT_PATH.exists(), "startup_safety_report.json is missing"

    def test_top_level_fields(self):
        report = load_report()
        for field in [
            "report_version",
            "equipment_id",
            "target_temp_c",
            "high_limit_c",
            "hold_requirement_sec",
            "phases",
            "safety_log",
            "interlock_audit",
            "summary",
            "safety_proof",
        ]:
            assert field in report, f"missing top-level field: {field}"

        assert report["report_version"] == 1
        assert report["target_temp_c"] == 24.0
        assert report["high_limit_c"] == 27.0
        assert report["hold_requirement_sec"] == 120.0
        assert isinstance(report["equipment_id"], str) and report["equipment_id"]


class TestPhaseLogs:
    def test_phase_presence_and_non_empty(self):
        report = load_report()
        for phase_name in ["trial_heat", "closed_loop"]:
            assert phase_name in report["phases"], f"missing phase: {phase_name}"
            assert "data" in report["phases"][phase_name], f"missing data for {phase_name}"
            assert get_phase_data(report, phase_name), f"{phase_name} data is empty"

    def test_sample_shape_and_ranges(self):
        report = load_report()
        for phase_name in ["trial_heat", "closed_loop"]:
            phase_data = get_phase_data(report, phase_name)
            last_time = None
            for index, sample in enumerate(phase_data):
                for field in [
                    "time_sec",
                    "pre_command_temp_c",
                    "measured_temp_c",
                    "raw_command_pct",
                    "applied_command_pct",
                    "high_limit_checked",
                    "limit_triggered",
                ]:
                    assert field in sample, f"{phase_name}[{index}] missing {field}"

                assert sample["high_limit_checked"] is True, f"{phase_name}[{index}] did not record the pre-check"
                assert 0.0 <= sample["applied_command_pct"] <= 100.0, \
                    f"{phase_name}[{index}] applied_command_pct out of range"

                if last_time is not None:
                    assert sample["time_sec"] > last_time, f"{phase_name} timestamps are not strictly increasing"
                last_time = sample["time_sec"]

    def test_limit_cutoff_behavior_in_startup_samples(self):
        report = load_report()
        all_samples = get_phase_data(report, "trial_heat") + get_phase_data(report, "closed_loop")
        for index, sample in enumerate(all_samples):
            if sample["pre_command_temp_c"] >= report["high_limit_c"]:
                assert sample["applied_command_pct"] == 0.0, \
                    f"sample {index} failed to cut heater power at or above the high limit"


class TestAuditAndEvents:
    def test_interlock_audit_forces_zero_command(self):
        report = load_report()
        audit = report["interlock_audit"]
        assert audit["measured_temp_c"] >= 27.2
        assert audit["raw_command_pct"] > 0.0
        assert audit["applied_command_pct"] == 0.0
        assert audit["limit_triggered"] is True
        assert audit["event_logged"] is True

    def test_audit_event_is_logged(self):
        report = load_report()
        events = report["safety_log"]["events"]
        assert isinstance(events, list) and events, "safety_log.events must include the audit cutoff"

        matching = [
            event
            for event in events
            if event["phase"] == "interlock_audit"
            and event["applied_command_pct"] == 0.0
            and event["reason"] == "high_limit_cutoff"
        ]
        assert matching, "missing interlock_audit event in safety_log"


class TestPerformance:
    def test_target_and_hold_requirement(self):
        report = load_report()
        closed_loop = get_phase_data(report, "closed_loop")
        hold_duration = compute_contiguous_hold_duration(closed_loop, report["target_temp_c"])
        assert hold_duration >= 120.0, f"contiguous hold duration {hold_duration}s is below 120s"
        assert report["summary"]["target_reached"] is True
        assert report["summary"]["hold_duration_sec"] >= 120.0

    def test_high_limit_never_exceeded(self):
        report = load_report()
        all_samples = get_phase_data(report, "trial_heat") + get_phase_data(report, "closed_loop")
        max_temp = max(sample["measured_temp_c"] for sample in all_samples)
        assert max_temp < 27.0, f"max measured temperature {max_temp}C exceeded the high limit"
        assert report["summary"]["never_exceeded_high_limit"] is True

    def test_summary_consistency(self):
        report = load_report()
        trial = get_phase_data(report, "trial_heat")
        closed_loop = get_phase_data(report, "closed_loop")
        all_samples = trial + closed_loop
        max_temp = max(sample["measured_temp_c"] for sample in all_samples)

        assert abs(report["summary"]["max_measured_temp_c"] - max_temp) < 1e-6
        assert abs(report["safety_proof"]["max_recorded_temp_c"] - max_temp) < 1e-6
        assert report["summary"]["trial_duration_sec"] == trial[-1]["time_sec"]
        assert report["summary"]["startup_duration_sec"] == all_samples[-1]["time_sec"]
        expected_closed_loop_duration = round(all_samples[-1]["time_sec"] - trial[-1]["time_sec"], 2)
        assert report["summary"]["closed_loop_duration_sec"] == expected_closed_loop_duration


class TestSafetyProof:
    def test_safety_proof_matches_log(self):
        report = load_report()
        all_samples = get_phase_data(report, "trial_heat") + get_phase_data(report, "closed_loop")
        commands_after_limit = [
            sample["applied_command_pct"]
            for sample in all_samples
            if sample["pre_command_temp_c"] >= report["high_limit_c"]
        ]
        expected_max_command = max(commands_after_limit) if commands_after_limit else 0.0

        proof = report["safety_proof"]
        assert proof["high_limit_respected"] is True
        assert proof["samples_checked"] == len(all_samples)
        assert proof["max_command_when_at_or_above_limit_pct"] == expected_max_command
