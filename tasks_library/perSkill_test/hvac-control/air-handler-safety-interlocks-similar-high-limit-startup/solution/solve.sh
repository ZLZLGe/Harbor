#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TASK_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

if [ -f /root/startup_profile.json ] && [ -f /root/air_handler_simulator.py ]; then
    ASSET_ROOT=/root
    OUTPUT_ROOT=/root
else
    ASSET_ROOT="$TASK_DIR/environment"
    OUTPUT_ROOT="$TASK_DIR"
fi

export ASSET_ROOT
export OUTPUT_ROOT

python3 <<'PY'
import json
import os
import sys
from pathlib import Path


asset_root = Path(os.environ["ASSET_ROOT"])
output_root = Path(os.environ["OUTPUT_ROOT"])
sys.path.insert(0, str(asset_root))

from air_handler_simulator import AirHandlerSimulator


with open(asset_root / "startup_profile.json", "r", encoding="utf-8") as fh:
    profile = json.load(fh)


def apply_high_limit(measured_temp_c, raw_command_pct, phase, time_sec, event_log):
    applied = max(0.0, min(100.0, float(raw_command_pct)))
    triggered = measured_temp_c >= profile["high_limit_c"]
    if triggered:
        applied = 0.0
        event_log.append(
            {
                "phase": phase,
                "time_sec": round(time_sec, 2),
                "measured_temp_c": round(measured_temp_c, 4),
                "raw_command_pct": round(float(raw_command_pct), 4),
                "applied_command_pct": 0.0,
                "reason": "high_limit_cutoff",
            }
        )
    return round(applied, 4), triggered


def build_sample(result, pre_temp_c, raw_command_pct, applied_command_pct, triggered):
    return {
        "time_sec": round(result["time_sec"], 2),
        "pre_command_temp_c": round(pre_temp_c, 4),
        "measured_temp_c": round(result["supply_temp_c"], 4),
        "raw_command_pct": round(float(raw_command_pct), 4),
        "applied_command_pct": round(float(applied_command_pct), 4),
        "high_limit_checked": True,
        "limit_triggered": bool(triggered),
    }


sim = AirHandlerSimulator(str(asset_root / "startup_profile.json"))
sim.reset()

trial_data = []
closed_loop_data = []
safety_events = []
dt_sec = profile["dt_sec"]
target_temp_c = profile["target_temp_c"]
hold_requirement_sec = profile["hold_requirement_sec"]


while sim.time_sec < profile["max_startup_time_sec"]:
    pre_temp_c = sim.read_temperature()
    raw_command_pct = profile["trial_boost_pct"]
    applied_command_pct, triggered = apply_high_limit(
        pre_temp_c, raw_command_pct, "trial_heat", sim.time_sec, safety_events
    )
    result = sim.step(applied_command_pct)
    trial_data.append(
        build_sample(result, pre_temp_c, raw_command_pct, applied_command_pct, triggered)
    )
    if result["supply_temp_c"] >= profile["trial_handoff_temp_c"]:
        break


integral = 0.0
hold_duration_sec = 0.0
while sim.time_sec < profile["max_startup_time_sec"]:
    pre_temp_c = sim.read_temperature()
    error = target_temp_c - pre_temp_c
    integral += error * dt_sec
    integral = max(-200.0, min(200.0, integral))

    raw_command_pct = (
        profile["nominal_hold_power_pct"] + (10.0 * error) + (0.25 * integral)
    )
    applied_command_pct, triggered = apply_high_limit(
        pre_temp_c, raw_command_pct, "closed_loop", sim.time_sec, safety_events
    )
    if triggered:
        integral = 0.0

    result = sim.step(applied_command_pct)
    closed_loop_data.append(
        build_sample(result, pre_temp_c, raw_command_pct, applied_command_pct, triggered)
    )

    if result["supply_temp_c"] >= target_temp_c:
        hold_duration_sec += dt_sec
    else:
        hold_duration_sec = 0.0

    if hold_duration_sec >= hold_requirement_sec:
        break


before_audit_events = len(safety_events)
audit_applied_pct, audit_triggered = apply_high_limit(
    27.2, 45.0, "interlock_audit", 0.0, safety_events
)
interlock_audit = {
    "measured_temp_c": 27.2,
    "raw_command_pct": 45.0,
    "applied_command_pct": audit_applied_pct,
    "limit_triggered": audit_triggered,
    "event_logged": len(safety_events) == before_audit_events + 1,
}


all_samples = trial_data + closed_loop_data
max_measured_temp_c = max(sample["measured_temp_c"] for sample in all_samples)
trial_duration_sec = trial_data[-1]["time_sec"] if trial_data else 0.0
startup_duration_sec = all_samples[-1]["time_sec"] if all_samples else 0.0
closed_loop_duration_sec = round(startup_duration_sec - trial_duration_sec, 2)

commands_when_at_or_above_limit = [
    sample["applied_command_pct"]
    for sample in all_samples
    if sample["pre_command_temp_c"] >= profile["high_limit_c"]
]
max_command_when_at_or_above_limit_pct = (
    max(commands_when_at_or_above_limit) if commands_when_at_or_above_limit else 0.0
)

report = {
    "report_version": 1,
    "equipment_id": profile["equipment_id"],
    "target_temp_c": target_temp_c,
    "high_limit_c": profile["high_limit_c"],
    "hold_requirement_sec": hold_requirement_sec,
    "phases": {
        "trial_heat": {
            "strategy": "fixed_boost_until_handoff",
            "data": trial_data,
        },
        "closed_loop": {
            "strategy": "feedback_trim",
            "data": closed_loop_data,
        },
    },
    "safety_log": {
        "events": safety_events,
    },
    "interlock_audit": interlock_audit,
    "summary": {
        "target_reached": any(sample["measured_temp_c"] >= target_temp_c for sample in all_samples),
        "hold_duration_sec": round(hold_duration_sec, 2),
        "trial_duration_sec": round(trial_duration_sec, 2),
        "closed_loop_duration_sec": round(closed_loop_duration_sec, 2),
        "startup_duration_sec": round(startup_duration_sec, 2),
        "max_measured_temp_c": round(max_measured_temp_c, 4),
        "never_exceeded_high_limit": max_measured_temp_c < profile["high_limit_c"],
    },
    "safety_proof": {
        "high_limit_respected": max_measured_temp_c < profile["high_limit_c"],
        "samples_checked": len(all_samples),
        "max_command_when_at_or_above_limit_pct": round(
            max_command_when_at_or_above_limit_pct, 4
        ),
        "max_recorded_temp_c": round(max_measured_temp_c, 4),
    },
}


with open(output_root / "startup_safety_report.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)
PY
