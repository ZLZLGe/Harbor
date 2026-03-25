#!/bin/bash

set -euo pipefail

INPUT_DIR="${EDGE_INPUT_DIR:-/root/edge_inputs}"
OUTPUT_FILE="${EDGE_OUTPUT_FILE:-/root/edge_trigger_strategy.json}"

python3 <<'PY'
import csv
import json
import os
from statistics import mean

input_dir = os.environ.get("EDGE_INPUT_DIR", "/root/edge_inputs")
output_file = os.environ.get("EDGE_OUTPUT_FILE", "/root/edge_trigger_strategy.json")

with open(os.path.join(input_dir, "hardware_profile.json"), "r", encoding="utf-8") as fh:
    hardware = json.load(fh)

with open(os.path.join(input_dir, "realtime_constraints.json"), "r", encoding="utf-8") as fh:
    constraints = json.load(fh)

with open(os.path.join(input_dir, "operator_brief.md"), "r", encoding="utf-8") as fh:
    brief = fh.read().lower()

with open(os.path.join(input_dir, "single_station_summary.csv"), "r", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

noise = mean(float(row["noise_floor_norm"]) for row in rows)
duration = mean(float(row["typical_spike_duration_seconds"]) for row in rows)

tight_latency = (
    constraints["channel_count"] == 1
    and constraints["max_trigger_latency_seconds"] <= 1.5
    and constraints["max_processing_ms_per_second"] <= 100
)
no_accelerator = hardware["accelerator"] == "none" and hardware["reserved_cores_for_trigger"] <= 1
no_templates = "no historical event library" in brief or "no historical template" in brief

if tight_latency and no_accelerator and no_templates:
    method_name = "sta_lta"
else:
    method_name = "deep_learning"

sta_window = 0.6 if duration <= 1.1 else 0.8
lta_window = 8.0 if noise >= 0.35 else 6.0
trigger_ratio = 3.4 if constraints["max_false_triggers_per_day"] >= 3 else 3.8
if noise > 0.42:
    trigger_ratio += 0.2
detrigger_ratio = 1.5
cooldown_seconds = 2.0 if duration < 1.2 else 3.0

result = {
    "method_name": method_name,
    "key_parameters": [
        {"name": "sta_window_seconds", "value": round(sta_window, 2)},
        {"name": "lta_window_seconds", "value": round(lta_window, 2)},
        {"name": "trigger_ratio", "value": round(trigger_ratio, 2)},
        {"name": "detrigger_ratio", "value": round(detrigger_ratio, 2)},
        {"name": "cooldown_seconds", "value": round(cooldown_seconds, 2)},
    ],
    "reason": (
        "STA/LTA fits this box because one CPU core must keep up with a 1.2 s trigger budget and there is no accelerator. "
        "The site can tolerate some extra internal alerts, and there is no template library for a heavier or template-driven approach."
    ),
}

os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)
    fh.write("\n")
PY
