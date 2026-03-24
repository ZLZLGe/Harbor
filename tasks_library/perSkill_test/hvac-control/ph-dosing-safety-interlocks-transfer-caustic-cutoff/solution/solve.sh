#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
cd "$ROOT_DIR"

python3 <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from ph_dosing_simulator import PhDosingSimulator


ROOT = Path(".")
OUTPUT_PATH = ROOT / "dosing_interlock_audit.json"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_command(measured_ph: float, raw_pct: float, low: float, high: float, limit_ph: float):
    if measured_ph >= limit_ph:
        return 0.0, True, False
    applied_pct = clamp(raw_pct, low, high)
    command_clamped = abs(applied_pct - raw_pct) > 1e-9
    return round(applied_pct, 4), False, command_clamped


def build_event(phase: str, time_sec: float, measured_ph: float, raw_pct: float, applied_pct: float, event_type: str):
    return {
        "phase": phase,
        "time_sec": round(time_sec, 2),
        "measured_ph": round(measured_ph, 4),
        "raw_caustic_pct": round(raw_pct, 4),
        "applied_caustic_pct": round(applied_pct, 4),
        "event_type": event_type,
    }


sim = PhDosingSimulator(str(ROOT / "dosing_profile.json"))
profile = sim.get_profile()
target_ph = float(profile["target_ph"])
band_low = float(profile["target_band"]["low"])
band_high = float(profile["target_band"]["high"])
limit_ph = float(profile["high_limit_ph"])
pump_min = float(profile["pump_limits_pct"]["min"])
pump_max = float(profile["pump_limits_pct"]["max"])

events = []


def run_trial_phase():
    samples = []
    sim.reset("trial_dose")
    for raw_pct in profile["trial_dose"]["requested_profile_pct"]:
        pre_command_ph = sim.read_ph()
        applied_pct, high_limit_triggered, command_clamped = safe_command(
            pre_command_ph, float(raw_pct), pump_min, pump_max, limit_ph
        )
        result = sim.step(applied_pct)
        sample = {
            "time_sec": result["time_sec"],
            "pre_command_ph": round(pre_command_ph, 4),
            "measured_ph": result["measured_ph"],
            "raw_caustic_pct": round(float(raw_pct), 4),
            "applied_caustic_pct": result["applied_caustic_pct"],
            "safety_checked": True,
            "high_limit_triggered": high_limit_triggered,
            "command_clamped": command_clamped,
        }
        samples.append(sample)

        if high_limit_triggered:
            events.append(
                build_event(
                    "trial_dose",
                    sample["time_sec"],
                    sample["pre_command_ph"],
                    sample["raw_caustic_pct"],
                    sample["applied_caustic_pct"],
                    "high_ph_cutoff",
                )
            )
        elif command_clamped:
            events.append(
                build_event(
                    "trial_dose",
                    sample["time_sec"],
                    sample["pre_command_ph"],
                    sample["raw_caustic_pct"],
                    sample["applied_caustic_pct"],
                    "command_clamped_to_range",
                )
            )
    return samples


def run_regulate_phase():
    samples = []
    sim.reset("regulate")
    duration_steps = int(profile["regulate"]["duration_sec"] / profile["dt_sec"])
    kp = float(profile["regulate"]["kp"])
    bias_pct = float(profile["regulate"]["bias_pct"])

    for _ in range(duration_steps):
        pre_command_ph = sim.read_ph()
        raw_pct = bias_pct + kp * (target_ph - pre_command_ph)
        raw_pct = round(raw_pct, 4)
        applied_pct, high_limit_triggered, command_clamped = safe_command(
            pre_command_ph, raw_pct, pump_min, pump_max, limit_ph
        )
        result = sim.step(applied_pct)
        sample = {
            "time_sec": result["time_sec"],
            "pre_command_ph": round(pre_command_ph, 4),
            "measured_ph": result["measured_ph"],
            "raw_caustic_pct": raw_pct,
            "applied_caustic_pct": result["applied_caustic_pct"],
            "safety_checked": True,
            "high_limit_triggered": high_limit_triggered,
            "command_clamped": command_clamped,
        }
        samples.append(sample)

        if high_limit_triggered:
            events.append(
                build_event(
                    "regulate",
                    sample["time_sec"],
                    sample["pre_command_ph"],
                    sample["raw_caustic_pct"],
                    sample["applied_caustic_pct"],
                    "high_ph_cutoff",
                )
            )
        elif command_clamped:
            events.append(
                build_event(
                    "regulate",
                    sample["time_sec"],
                    sample["pre_command_ph"],
                    sample["raw_caustic_pct"],
                    sample["applied_caustic_pct"],
                    "command_clamped_to_range",
                )
            )
    return samples


def run_audit_case(case_name: str, measured_ph: float, raw_pct: float):
    applied_pct, high_limit_triggered, command_clamped = safe_command(
        measured_ph, raw_pct, pump_min, pump_max, limit_ph
    )
    event_type = "high_ph_cutoff" if high_limit_triggered else "command_clamped_to_range"
    events.append(build_event(case_name, 0.0, measured_ph, raw_pct, applied_pct, event_type))
    return {
        "measured_ph": round(measured_ph, 4),
        "raw_caustic_pct": round(raw_pct, 4),
        "applied_caustic_pct": round(applied_pct, 4),
        "high_limit_triggered": high_limit_triggered,
        "command_clamped": command_clamped,
        "event_logged": True,
    }


trial_samples = run_trial_phase()
regulate_samples = run_regulate_phase()

audit_cases = {
    "cutoff_probe": run_audit_case("cutoff_probe", 7.24, 18.0),
    "clamp_probe": run_audit_case("clamp_probe", 6.18, 58.0),
}

all_samples = trial_samples + regulate_samples
tail_window = int(profile["regulate"]["tail_window_samples"])
tail_samples = regulate_samples[-tail_window:]
tail_mae = sum(abs(target_ph - sample["measured_ph"]) for sample in tail_samples) / tail_window
samples_at_or_above_limit = [
    sample for sample in all_samples if sample["pre_command_ph"] >= limit_ph
]
clamp_events = [event for event in events if event["event_type"] == "command_clamped_to_range"]
cutoff_events = [event for event in events if event["event_type"] == "high_ph_cutoff"]

report = {
    "report_version": 1,
    "fermentor_id": profile["fermentor_id"],
    "target_ph": target_ph,
    "target_band": profile["target_band"],
    "high_limit_ph": limit_ph,
    "pump_limits_pct": profile["pump_limits_pct"],
    "phases": {
        "trial_dose": {
            "requested_profile_pct": profile["trial_dose"]["requested_profile_pct"],
            "data": trial_samples,
        },
        "regulate": {
            "strategy": "proportional_trim",
            "tail_window_samples": tail_window,
            "data": regulate_samples,
        },
    },
    "event_log": {
        "events": events,
    },
    "audit_cases": audit_cases,
    "summary": {
        "trial_peak_ph": round(max(sample["measured_ph"] for sample in trial_samples), 4),
        "regulate_final_ph": regulate_samples[-1]["measured_ph"],
        "regulate_tail_samples": tail_window,
        "regulate_tail_mean_abs_error": round(tail_mae, 4),
        "final_in_target_band": band_low <= regulate_samples[-1]["measured_ph"] <= band_high,
        "samples_at_or_above_limit": len(samples_at_or_above_limit),
        "max_applied_command_when_at_or_above_limit_pct": round(
            max(
                (sample["applied_caustic_pct"] for sample in samples_at_or_above_limit),
                default=0.0,
            ),
            4,
        ),
    },
    "compliance": {
        "high_ph_cutoff_respected": all(
            sample["applied_caustic_pct"] == 0.0 for sample in samples_at_or_above_limit
        ),
        "command_clamp_respected": all(
            pump_min <= sample["applied_caustic_pct"] <= pump_max for sample in all_samples
        ),
        "logged_event_count": len(events),
        "cutoff_event_count": len(cutoff_events),
        "clamp_event_count": len(clamp_events),
    },
}

OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
PY
