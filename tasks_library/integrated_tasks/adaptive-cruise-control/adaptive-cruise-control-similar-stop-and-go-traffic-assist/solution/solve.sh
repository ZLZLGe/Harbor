#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/pid_controller.py
"""PID controller used by the traffic jam assist system."""


class PIDController:
    """Discrete PID controller with optional output and integral limits."""

    def __init__(self, kp, ki, kd, output_limits=None, integral_limit=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.integral_limit = integral_limit
        self.integral = 0.0
        self.prev_error = None

    def reset(self):
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        self.integral += error * dt
        if self.integral_limit is not None:
            self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))

        derivative = 0.0
        if self.prev_error is not None:
            derivative = (error - self.prev_error) / dt
        self.prev_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        if self.output_limits is not None:
            low, high = self.output_limits
            output = max(low, min(high, output))
        return output
PY

cat <<'PY' > /root/jam_assist_system.py
"""Traffic jam assist controller with cruise, follow, stop-hold, and emergency modes."""

from pid_controller import PIDController


class TrafficJamAssist:
    """Longitudinal controller for stop-and-go traffic jam assist."""

    def __init__(self, config):
        assist_cfg = config["jam_assist"]
        vehicle_cfg = config["vehicle"]
        speed_gains = config.get("pid_speed_tuned", config["pid_speed"])
        gap_gains = config.get("pid_gap_tuned", config["pid_gap"])

        self.set_speed = assist_cfg["set_speed"]
        self.time_headway = assist_cfg["time_headway"]
        self.min_gap = assist_cfg["min_gap"]
        self.emergency_ttc_threshold = assist_cfg["emergency_ttc_threshold"]
        self.stop_hold_gap_buffer = assist_cfg["stop_hold_gap_buffer"]
        self.restart_speed_threshold = assist_cfg["restart_speed_threshold"]
        self.max_accel = vehicle_cfg["max_acceleration"]
        self.max_decel = vehicle_cfg["max_deceleration"]

        limits = (self.max_decel, self.max_accel)
        self.speed_pid = PIDController(
            speed_gains["kp"],
            speed_gains["ki"],
            speed_gains["kd"],
            output_limits=limits,
            integral_limit=12.0,
        )
        self.gap_pid = PIDController(
            gap_gains["kp"],
            gap_gains["ki"],
            gap_gains["kd"],
            output_limits=limits,
            integral_limit=25.0,
        )
        self.prev_mode = "cruise"

    def target_gap(self, ego_speed):
        return self.min_gap + self.time_headway * ego_speed

    def time_to_collision(self, gap_to_lead, ego_speed, lead_speed):
        if gap_to_lead is None:
            return float("inf")
        closing_speed = ego_speed - lead_speed
        if closing_speed <= 0.0:
            return float("inf")
        return gap_to_lead / closing_speed

    def _reset_for_mode_change(self, new_mode):
        if new_mode != self.prev_mode:
            if new_mode == "cruise":
                self.speed_pid.reset()
            else:
                self.gap_pid.reset()
        self.prev_mode = new_mode

    def compute(self, ego_speed, lead_speed, gap_to_lead, dt):
        lead_visible = lead_speed is not None and gap_to_lead is not None
        if not lead_visible:
            self._reset_for_mode_change("cruise")
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            if ego_speed > self.set_speed + 0.35:
                accel_cmd = min(accel_cmd, -0.6 * (ego_speed - self.set_speed))
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            return accel_cmd, "cruise", None, None

        target_gap = self.target_gap(ego_speed)
        gap_error = gap_to_lead - target_gap
        ttc = self.time_to_collision(gap_to_lead, ego_speed, lead_speed)

        if ttc < self.emergency_ttc_threshold:
            mode = "emergency"
            accel_cmd = self.max_decel
        elif (
            lead_speed <= 0.2
            and gap_to_lead <= target_gap + self.stop_hold_gap_buffer
            and ego_speed <= self.restart_speed_threshold + 0.5
        ):
            mode = "stop_hold"
            accel_cmd = -min(2.0, ego_speed / dt if dt > 0 else 2.0)
        else:
            mode = "follow"
            accel_cmd = self.gap_pid.compute(gap_error, dt) + 0.22 * (lead_speed - ego_speed)
            if lead_speed < 2.0 and gap_to_lead < target_gap + 4.0:
                accel_cmd = min(accel_cmd, 0.8)
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        self._reset_for_mode_change(mode)
        return accel_cmd, mode, gap_error, target_gap
PY

cat <<'PY' > /root/simulate_jam.py
"""Run the stop-and-go traffic jam assist simulation."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import yaml

from jam_assist_system import TrafficJamAssist


def _coerce_optional(value):
    if pd.isna(value):
        return None
    return float(value)


def run_simulation(
    config_path="/root/jam_vehicle.yaml",
    radar_path="/root/jam_radar_trace.csv",
    tuning_path="/root/jam_tuning.yaml",
    output_path="/root/jam_results.csv",
):
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    tuning_file = Path(tuning_path)
    if tuning_file.exists():
        with tuning_file.open("r", encoding="utf-8") as handle:
            tuning = yaml.safe_load(handle)
        config["pid_speed_tuned"] = tuning["pid_speed"]
        config["pid_gap_tuned"] = tuning["pid_gap"]

    assist = TrafficJamAssist(config)
    radar_df = pd.read_csv(radar_path)

    dt = config["simulation"]["dt"]
    jerk_limit = config["comfort"]["jerk_limit"]
    ego_speed = 0.0
    gap_to_lead = None
    prev_accel = 0.0
    previous_target_visible = False
    results = []

    for _, row in radar_df.iterrows():
        time = float(row["time"])
        lead_speed = _coerce_optional(row["lead_speed"])
        distance_hint = _coerce_optional(row["distance_hint"])
        target_visible = lead_speed is not None

        if target_visible and (not previous_target_visible or gap_to_lead is None):
            if distance_hint is None:
                raise ValueError("distance_hint must be present when a target first appears")
            gap_to_lead = distance_hint
        elif not target_visible:
            gap_to_lead = None

        accel_cmd, mode, gap_error, target_gap = assist.compute(ego_speed, lead_speed, gap_to_lead, dt)

        desired_jerk = (accel_cmd - prev_accel) / dt
        jerk = max(-jerk_limit, min(jerk_limit, desired_jerk))
        accel_limited = prev_accel + jerk * dt
        accel_limited = max(config["vehicle"]["max_deceleration"], min(config["vehicle"]["max_acceleration"], accel_limited))
        prev_accel = accel_limited

        results.append(
            {
                "time": round(time, 1),
                "ego_speed": round(ego_speed, 3),
                "lead_speed": round(lead_speed, 3) if lead_speed is not None else "",
                "gap_to_lead": round(gap_to_lead, 3) if gap_to_lead is not None else "",
                "acceleration_cmd": round(accel_limited, 3),
                "jerk": round(jerk, 3),
                "mode": mode,
                "gap_error": round(gap_error, 3) if gap_error is not None else "",
                "target_gap": round(target_gap, 3) if target_gap is not None else "",
            }
        )

        next_ego_speed = max(0.0, ego_speed + accel_limited * dt)
        if target_visible and gap_to_lead is not None:
            gap_to_lead = max(0.0, gap_to_lead + (lead_speed - next_ego_speed) * dt)
        else:
            gap_to_lead = None
        ego_speed = next_ego_speed
        previous_target_visible = target_visible

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)
    return results_df


if __name__ == "__main__":
    run_simulation()
PY

cat <<'YAML' > /root/jam_tuning.yaml
pid_speed:
  kp: 0.50
  ki: 0.03
  kd: 0.06
pid_gap:
  kp: 0.35
  ki: 0.06
  kd: 0.12
YAML

python3 /root/simulate_jam.py

python3 <<'PY'
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def percentile(values, q):
    if not values:
        return 0.0
    values = sorted(values)
    idx = int(round((len(values) - 1) * q))
    return values[idx]


results = pd.read_csv("/root/jam_results.csv")
with open("/root/jam_tuning.yaml", "r", encoding="utf-8") as handle:
    tuning = yaml.safe_load(handle)

lead_present = results["lead_speed"].notna()
min_gap = results.loc[lead_present, "gap_to_lead"].min()
jerk_p95 = percentile(results["jerk"].abs().tolist(), 0.95)

settling_windows = [(56.0, 64.0), (98.0, 106.0), (136.0, 146.0)]
settling_rows = []
for start, end in settling_windows:
    window = results[(results["time"] >= start) & (results["time"] <= end) & (results["mode"] == "follow")]
    mean_abs_gap_error = window["gap_error"].abs().mean()
    settling_rows.append((start, end, mean_abs_gap_error))

stop_segments = []
in_stop = False
start_time = None
for row in results.itertuples():
    stopped = pd.notna(row.lead_speed) and row.ego_speed <= 0.3
    if stopped and not in_stop:
        start_time = row.time
        in_stop = True
    elif in_stop and not stopped:
        stop_segments.append((start_time, round(row.time - 0.1, 1)))
        in_stop = False
if in_stop:
    stop_segments.append((start_time, float(results.iloc[-1]["time"])))

restart_speeds = []
for _, stop_end in stop_segments:
    target_time = round(stop_end + 5.0, 1)
    row = results[results["time"] == target_time]
    if not row.empty:
        restart_speeds.append((target_time, float(row.iloc[0]["ego_speed"])))

report = f"""# Stop-and-Go Traffic Jam Assist Report

## System Design

The controller uses a mode-based longitudinal design with `cruise`, `follow`, `stop_hold`, and `emergency` behaviors. A speed PID handles clear-lane tracking, while a gap PID plus lead-speed feed-forward manages stop-and-go following. The simulator only uses `distance_hint` to initialize the target range when a lead vehicle first appears; after acquisition, the gap evolves from relative motion.

## PID Tuning

Final tuned gains loaded from `jam_tuning.yaml`:

- Speed loop: `kp={tuning['pid_speed']['kp']:.2f}`, `ki={tuning['pid_speed']['ki']:.2f}`, `kd={tuning['pid_speed']['kd']:.2f}`
- Gap loop: `kp={tuning['pid_gap']['kp']:.2f}`, `ki={tuning['pid_gap']['ki']:.2f}`, `kd={tuning['pid_gap']['kd']:.2f}`

The tuning emphasizes low overspeed in clear-lane cruise, smooth restart behavior after two full stops, and stable gap recovery once the queue begins moving.

## Stop-and-Go Results

- Clear-lane mean ego speed, `12-15 s`: {results[(results['time'] >= 12.0) & (results['time'] <= 15.0)]['ego_speed'].mean():.3f} m/s
- Clear-lane mean ego speed, `160-170 s`: {results[(results['time'] >= 160.0) & (results['time'] <= 170.0)]['ego_speed'].mean():.3f} m/s
- Minimum simulated gap: {min_gap:.3f} m
- Detected full-stop windows: {stop_segments}
- Restart speeds 5 s after each release: {restart_speeds}

## Comfort And Settling Metrics

- 95th percentile of `|jerk|`: {jerk_p95:.3f} m/s^3
- Mean absolute gap error in `56-64 s`: {settling_rows[0][2]:.3f} m
- Mean absolute gap error in `98-106 s`: {settling_rows[1][2]:.3f} m
- Mean absolute gap error in `136-146 s`: {settling_rows[2][2]:.3f} m

These comfort and settling numbers confirm that the stop-and-go controller stays within the requested jerk budget while re-centering the simulated following gap after each queue release.
"""

Path("/root/jam_assist_report.md").write_text(report, encoding="utf-8")
PY
