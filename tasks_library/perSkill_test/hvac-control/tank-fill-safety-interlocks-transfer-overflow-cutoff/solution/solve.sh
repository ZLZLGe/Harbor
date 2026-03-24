#!/bin/bash
set -e

python3 <<'PY'
#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path


def resolve_root() -> Path:
    env_root = os.environ.get("TASK_ROOT")
    if env_root:
        return Path(env_root)
    root_candidate = Path("/root")
    try:
        if (root_candidate / "tank_fill_simulator.py").exists():
            return root_candidate
    except PermissionError:
        pass
    return Path.cwd().parent / "environment"


ROOT = resolve_root()
sys.path.insert(0, str(ROOT))

from tank_fill_simulator import TankFillSimulator  # noqa: E402


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def apply_interlock(
    *,
    phase_name: str,
    time_sec: float,
    measured_level_pct: float,
    requested_inlet_pct: float,
    freeze_state: bool,
    high_level_pct: float,
    reopen_fill_pct: float,
    safety_events: list[dict],
) -> tuple[float, bool, bool]:
    if freeze_state and measured_level_pct < reopen_fill_pct:
        freeze_state = False

    activated_now = False
    if measured_level_pct >= high_level_pct and not freeze_state:
        freeze_state = True
        activated_now = True
        safety_events.append(
            {
                "phase": phase_name,
                "time_sec": round(time_sec, 2),
                "measured_level_pct": round(measured_level_pct, 2),
                "requested_inlet_pct": round(requested_inlet_pct, 2),
                "applied_inlet_pct": 0.0,
                "reason": "high_level_cutoff",
            }
        )

    applied_inlet_pct = 0.0 if freeze_state else clamp(requested_inlet_pct, 0.0, 100.0)
    return round(applied_inlet_pct, 2), freeze_state, activated_now


def build_sample(pre_level: float, requested: float, applied: float, result: dict, frozen: bool) -> dict:
    return {
        "time_sec": result["time_sec"],
        "pre_command_level_pct": round(pre_level, 2),
        "measured_level_pct": result["measured_level_pct"],
        "requested_inlet_pct": round(requested, 2),
        "applied_inlet_pct": round(applied, 2),
        "high_level_checked": True,
        "interlock_active": frozen,
        "fill_frozen": frozen,
    }


def run_pulse_test(sim: TankFillSimulator, recipe: dict, safety_events: list[dict]) -> list[dict]:
    sim.reset("pulse_test")
    high_level_pct = float(recipe["high_level_interlock_pct"])
    reopen_fill_pct = float(recipe["reopen_fill_pct"])
    samples = []
    frozen = False

    for requested in recipe["pulse_test"]["requested_profile_pct"]:
        pre_level = sim.current_measurement()
        applied, frozen, _ = apply_interlock(
            phase_name="pulse_test",
            time_sec=sim.time_sec,
            measured_level_pct=pre_level,
            requested_inlet_pct=float(requested),
            freeze_state=frozen,
            high_level_pct=high_level_pct,
            reopen_fill_pct=reopen_fill_pct,
            safety_events=safety_events,
        )
        result = sim.step(applied)
        samples.append(build_sample(pre_level, float(requested), applied, result, frozen))

    return samples


def choose_fill_command(pre_level_pct: float, band_low: float, band_high: float) -> float:
    if pre_level_pct < band_low - 1.5:
        return 100.0
    if pre_level_pct < band_low:
        return 65.0
    if pre_level_pct < 86.0:
        return 24.0
    if pre_level_pct <= band_high:
        return 12.0
    return 0.0


def run_auto_fill(sim: TankFillSimulator, recipe: dict, safety_events: list[dict]) -> list[dict]:
    sim.reset("auto_fill")
    high_level_pct = float(recipe["high_level_interlock_pct"])
    reopen_fill_pct = float(recipe["reopen_fill_pct"])
    band_low = float(recipe["target_band_pct"]["low"])
    band_high = float(recipe["target_band_pct"]["high"])
    duration_sec = float(recipe["auto_fill"]["duration_sec"])
    steps = int(duration_sec / float(recipe["dt_sec"]))

    samples = []
    frozen = False

    for _ in range(steps):
        pre_level = sim.current_measurement()
        requested = choose_fill_command(pre_level, band_low, band_high)
        applied, frozen, _ = apply_interlock(
            phase_name="auto_fill",
            time_sec=sim.time_sec,
            measured_level_pct=pre_level,
            requested_inlet_pct=requested,
            freeze_state=frozen,
            high_level_pct=high_level_pct,
            reopen_fill_pct=reopen_fill_pct,
            safety_events=safety_events,
        )
        result = sim.step(applied)
        samples.append(build_sample(pre_level, requested, applied, result, frozen))

    return samples


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


def freeze_respected(samples: list[dict], reopen_fill_pct: float) -> bool:
    frozen = False
    for sample in samples:
        if sample["pre_command_level_pct"] >= 92.0:
            frozen = True
        elif frozen and sample["pre_command_level_pct"] < reopen_fill_pct:
            frozen = False

        if frozen and sample["applied_inlet_pct"] != 0.0:
            return False
    return True


def main() -> None:
    recipe_path = ROOT / "fill_recipe.json"
    with recipe_path.open("r", encoding="utf-8") as fh:
        recipe = json.load(fh)

    sim = TankFillSimulator(str(recipe_path))
    safety_events: list[dict] = []

    pulse_data = run_pulse_test(sim, recipe, safety_events)
    auto_fill_data = run_auto_fill(sim, recipe, safety_events)

    all_samples = pulse_data + auto_fill_data
    band_low = float(recipe["target_band_pct"]["low"])
    band_high = float(recipe["target_band_pct"]["high"])
    high_level_pct = float(recipe["high_level_interlock_pct"])
    reopen_fill_pct = float(recipe["reopen_fill_pct"])
    overflow_level_pct = float(recipe["overflow_level_pct"])

    max_level_pct = max(sample["measured_level_pct"] for sample in all_samples)
    samples_at_or_above_interlock = [
        sample for sample in all_samples if sample["pre_command_level_pct"] >= high_level_pct
    ]
    max_applied_when_high = max(
        (sample["applied_inlet_pct"] for sample in samples_at_or_above_interlock),
        default=0.0,
    )
    contiguous_hold_sec = compute_contiguous_hold_sec(auto_fill_data, band_low, band_high)

    summary = {
        "report_version": 1,
        "tank_id": recipe["tank_id"],
        "target_band_pct": recipe["target_band_pct"],
        "high_level_interlock_pct": high_level_pct,
        "reopen_fill_pct": reopen_fill_pct,
        "phases": {
            "pulse_test": {
                "requested_profile_pct": recipe["pulse_test"]["requested_profile_pct"],
                "data": pulse_data,
            },
            "auto_fill": {
                "strategy": "band_fill_with_reopen_hysteresis",
                "data": auto_fill_data,
            },
        },
        "safety_log": {
            "events": safety_events,
        },
        "summary": {
            "target_band_reached": any(
                band_low <= sample["measured_level_pct"] <= band_high for sample in auto_fill_data
            ),
            "contiguous_hold_sec": contiguous_hold_sec,
            "final_level_pct": auto_fill_data[-1]["measured_level_pct"],
            "max_level_pct": max_level_pct,
            "interlock_event_count": len(safety_events),
            "never_overflowed": max_level_pct < overflow_level_pct,
        },
        "safety_proof": {
            "all_samples_checked": all(sample["high_level_checked"] for sample in all_samples),
            "samples_at_or_above_interlock": len(samples_at_or_above_interlock),
            "max_applied_inlet_at_or_above_interlock_pct": round(max_applied_when_high, 2),
            "freeze_respected_until_reopen": freeze_respected(all_samples, reopen_fill_pct),
            "overflow_margin_pct": round(overflow_level_pct - max_level_pct, 2),
        },
    }

    output_path = ROOT / "fill_interlock_summary.json"
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
PY
