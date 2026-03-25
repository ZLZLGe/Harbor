#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import csv
import json

from fan_spinup_simulator import FanSpinupSimulator


with open("/root/fan_bench_profile.json", "r", encoding="utf-8") as handle:
    profile = json.load(handle)

baseline_duration_s = 1.5
step_voltage_v = 7.2
hold_duration_s = 10.0

simulator = FanSpinupSimulator("/root/fan_bench_profile.json")
sample_period_s = profile["sample_period_s"]

rows = [simulator.reset()]

for _ in range(int(baseline_duration_s / sample_period_s)):
    rows.append(simulator.step(0.0))

for _ in range(int(hold_duration_s / sample_period_s)):
    rows.append(simulator.step(step_voltage_v))

with open("/root/spinup_trace.csv", "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["time_s", "drive_voltage_v", "measured_rpm"],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
