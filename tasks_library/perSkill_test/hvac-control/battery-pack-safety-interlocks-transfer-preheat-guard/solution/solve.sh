#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"

python3 <<'PY'
import json
import os
import sys

root = os.environ.get("TASK_ROOT", "/root")
sys.path.insert(0, root)

from battery_pack_simulator import BatteryPackSimulator


profile_path = os.path.join(root, "preheat_profile.json")
report_path = os.path.join(root, "battery_safety_report.json")

sim = BatteryPackSimulator(profile_path)
profile = sim.get_profile()
charge_min = float(profile["charge_window_c"]["min"])
charge_max = float(profile["charge_window_c"]["max"])
trip_temp = float(profile["cell_trip_temp_c"])
reset_temp = float(profile["cell_reset_temp_c"])

trajectory = []
interlock_events = []
interlock_active = False
had_trip = False


while True:
    snapshot = sim.snapshot()
    module_temp_c = snapshot["module_temp_c"]
    cell_temps_c = snapshot["cell_temps_c"]
    max_cell_temp_c = max(cell_temps_c)

    if max_cell_temp_c >= trip_temp:
        interlock_active = True
        if not had_trip:
            had_trip = True
    elif interlock_active and max_cell_temp_c < reset_temp:
        interlock_active = False

    charge_enable = (
        (not interlock_active)
        and charge_min <= module_temp_c <= charge_max
        and max_cell_temp_c < reset_temp
    )
    raw_heater_pct = 0.0 if charge_enable else 100.0
    applied_heater_pct = 0.0 if interlock_active else raw_heater_pct

    trajectory.append(
        {
            "time_sec": snapshot["time_sec"],
            "module_temp_c": module_temp_c,
            "cell_temps_c": cell_temps_c,
            "requested_heater_pct": raw_heater_pct,
            "applied_heater_pct": applied_heater_pct,
            "interlock_active": interlock_active,
            "charge_enable": charge_enable,
        }
    )

    if interlock_active and max_cell_temp_c >= trip_temp:
        if not interlock_events or interlock_events[-1]["time_sec"] != snapshot["time_sec"]:
            triggering_index = max(
                range(len(cell_temps_c)),
                key=lambda idx: cell_temps_c[idx],
            )
            interlock_events.append(
                {
                    "time_sec": snapshot["time_sec"],
                    "triggering_cell_index": triggering_index + 1,
                    "trigger_cell_temp_c": round(cell_temps_c[triggering_index], 2),
                    "requested_heater_pct": raw_heater_pct,
                    "applied_heater_pct": applied_heater_pct,
                    "charge_enable_after_cutoff": charge_enable,
                    "reason": "cell_overtemp_cutoff",
                }
            )

    if had_trip and charge_enable:
        break

    if snapshot["time_sec"] >= 240.0:
        break

    sim.step(applied_heater_pct)

final_sample = trajectory[-1]
final_max_cell_temp_c = round(max(final_sample["cell_temps_c"]), 2)
first_chargeable_time_sec = None
for sample in trajectory:
    if sample["charge_enable"]:
        first_chargeable_time_sec = sample["time_sec"]
        break

report = {
    "report_version": 1,
    "pack_id": profile["pack_id"],
    "charge_window_c": profile["charge_window_c"],
    "cell_trip_temp_c": trip_temp,
    "cell_reset_temp_c": reset_temp,
    "trajectory": trajectory,
    "interlock_events": interlock_events,
    "summary": {
        "trajectory_samples": len(trajectory),
        "interlock_trigger_times_sec": [event["time_sec"] for event in interlock_events],
        "interlock_trigger_count": len(interlock_events),
        "first_chargeable_time_sec": first_chargeable_time_sec,
        "final_module_temp_c": final_sample["module_temp_c"],
        "final_max_cell_temp_c": final_max_cell_temp_c,
        "final_charge_enable": final_sample["charge_enable"],
        "heater_forced_off_while_interlocked": all(
            sample["applied_heater_pct"] == 0.0
            for sample in trajectory
            if sample["interlock_active"]
        ),
    },
    "final_decision": {
        "charge_enable": final_sample["charge_enable"],
        "reason": (
            "module_in_window_and_cells_below_reset"
            if final_sample["charge_enable"]
            else "unsafe_or_not_ready"
        ),
        "module_temp_c": final_sample["module_temp_c"],
        "max_cell_temp_c": final_max_cell_temp_c,
    },
}

with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)
    fh.write("\n")
PY
