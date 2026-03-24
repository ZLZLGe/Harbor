#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import math
import os
import re
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.path.join(APP_ROOT, "data")
OUT_PATH = os.path.join(APP_ROOT, "output", "wave_solder_profile_audit.yaml")

HANDBOOK_PATH = os.path.join(DATA_DIR, "wave_solder_handbook.pdf")
LOT_PATH = os.path.join(DATA_DIR, "lot_manifest.csv")
TC_PATH = os.path.join(DATA_DIR, "wave_thermocouples.csv")
SPEED_PATH = os.path.join(DATA_DIR, "line_speed_log.csv")
DEFECT_PATH = os.path.join(DATA_DIR, "defect_ledger.csv")

FAILURE_REASON_ORDER = [
    "preheat_ramp_exceeds_limit",
    "entry_temp_out_of_window",
    "contact_time_out_of_window",
    "speed_out_of_window",
    "bridging_present",
    "insufficient_fill_present",
]


def round2(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return float(round(value, 2))


def read_handbook() -> Dict[str, float]:
    with open(HANDBOOK_PATH, "r", encoding="utf-8") as handle:
        text = handle.read()

    def extract(pattern: str) -> float:
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing handbook pattern: {pattern}")
        return float(match.group(1))

    return {
        "preheat_temp_min_c": extract(r"Evaluate ramp only in the ([0-9.]+) C to [0-9.]+ C"),
        "preheat_temp_max_c": extract(r"Evaluate ramp only in the [0-9.]+ C to ([0-9.]+) C"),
        "max_preheat_ramp_c_per_s": extract(r"Maximum allowed preheat ramp: ([0-9.]+) C/s"),
        "entry_temp_min_c": extract(r"temperature window: ([0-9.]+) C to [0-9.]+ C"),
        "entry_temp_max_c": extract(r"temperature window: [0-9.]+ C to ([0-9.]+) C"),
        "contact_time_threshold_c": extract(r"time above ([0-9.]+) C"),
        "contact_time_min_s": extract(r"Acceptable contact time window: ([0-9.]+) s to [0-9.]+ s"),
        "contact_time_max_s": extract(r"Acceptable contact time window: [0-9.]+ s to ([0-9.]+) s"),
        "effective_wave_contact_length_cm": extract(r"Effective wave contact length: ([0-9.]+) cm"),
        "speed_min_cm_min": extract(r"speed_min_cm_min = [0-9.]+ / [0-9.]+ \* 60 = ([0-9.]+)"),
        "speed_max_cm_min": extract(r"speed_max_cm_min = [0-9.]+ / [0-9.]+ \* 60 = ([0-9.]+)"),
        "target_entry_temp_c": extract(r"entry temperature target center: ([0-9.]+) C"),
        "target_contact_time_s": extract(r"contact time target center: ([0-9.]+) s"),
        "target_speed_cm_min": extract(r"conveyor speed target center: ([0-9.]+) cm/min"),
    }


def time_above_threshold(group: pd.DataFrame, threshold: float) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    times = group["time_s"].astype(float).tolist()
    temps = group["temp_c"].astype(float).tolist()
    total = 0.0
    has_segment = False
    for idx in range(1, len(group)):
        t0 = times[idx - 1]
        t1 = times[idx]
        y0 = temps[idx - 1]
        y1 = temps[idx]
        if t1 <= t0:
            continue
        has_segment = True
        if y0 > threshold and y1 > threshold:
            total += t1 - t0
            continue
        crosses = (y0 <= threshold < y1) or (y1 <= threshold < y0)
        if crosses and y1 != y0:
            fraction = (threshold - y0) / (y1 - y0)
            t_cross = t0 + fraction * (t1 - t0)
            if y0 <= threshold and y1 > threshold:
                total += t1 - t_cross
            else:
                total += t_cross - t0
    if not has_segment:
        return None
    return round2(total)


def max_preheat_ramp(group: pd.DataFrame, lower: float, upper: float) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    best = None
    times = group["time_s"].astype(float).tolist()
    temps = group["temp_c"].astype(float).tolist()
    for idx in range(1, len(group)):
        t0 = times[idx - 1]
        t1 = times[idx]
        y0 = temps[idx - 1]
        y1 = temps[idx]
        if t1 <= t0:
            continue
        if lower <= y0 <= upper and lower <= y1 <= upper:
            slope = (y1 - y0) / (t1 - t0)
            best = slope if best is None else max(best, slope)
    return round2(best)


def sorted_failure_reasons(failures: List[str]) -> List[str]:
    order = {code: idx for idx, code in enumerate(FAILURE_REASON_ORDER)}
    return sorted(failures, key=lambda code: order[code])


limits = read_handbook()
lots = pd.read_csv(LOT_PATH).sort_values(["lot_id"], kind="mergesort")
tc = pd.read_csv(TC_PATH).sort_values(["lot_id", "tc_id", "record_type", "time_s"], kind="mergesort")
speed = pd.read_csv(SPEED_PATH).sort_values(["lot_id", "stamp_s"], kind="mergesort")
defects = pd.read_csv(DEFECT_PATH).sort_values(["lot_id", "defect_type"], kind="mergesort")

for frame, key in [(lots, "lot_id"), (tc, "lot_id"), (speed, "lot_id"), (defects, "lot_id")]:
    frame[key] = frame[key].astype(str)
tc["tc_id"] = tc["tc_id"].astype(str)

lot_rows: List[Dict[str, Any]] = []

for _, lot in lots.iterrows():
    lot_id = str(lot["lot_id"])
    lot_tc = tc[tc["lot_id"] == lot_id]

    preheat = lot_tc[lot_tc["sensor_group"] == "top_preheat"]
    ramp_values = []
    for tc_id, group in preheat.groupby("tc_id", sort=False):
        ramp = max_preheat_ramp(group, limits["preheat_temp_min_c"], limits["preheat_temp_max_c"])
        if ramp is not None:
            ramp_values.append((float(ramp), str(tc_id)))
    max_ramp = round2(max(value for value, _ in ramp_values)) if ramp_values else None

    entry = lot_tc[(lot_tc["record_type"] == "entry_snapshot") & (lot_tc["sensor_group"] == "entry_top")]
    entry_choices = sorted(
        [(float(row["temp_c"]), str(row["tc_id"])) for _, row in entry.iterrows()],
        key=lambda item: (item[0], item[1]),
    )
    entry_temp = round2(entry_choices[0][0]) if entry_choices else None
    entry_sensor_id = entry_choices[0][1] if entry_choices else None

    wave = lot_tc[(lot_tc["record_type"] == "wave_trace") & (lot_tc["sensor_group"] == "wave_contact")]
    contact_choices: List[Tuple[float, str]] = []
    for tc_id, group in wave.groupby("tc_id", sort=False):
        contact_time = time_above_threshold(group, limits["contact_time_threshold_c"])
        if contact_time is not None:
            contact_choices.append((float(contact_time), str(tc_id)))
    contact_choices.sort(key=lambda item: (-item[0], item[1]))
    contact_time_s = round2(contact_choices[0][0]) if contact_choices else None
    contact_sensor_id = contact_choices[0][1] if contact_choices else None

    lot_speed = speed[speed["lot_id"] == lot_id]["speed_cm_min"].astype(float).tolist()
    actual_speed = round2(median(lot_speed)) if lot_speed else None

    lot_defects = defects[defects["lot_id"] == lot_id]
    bridge_count = int(lot_defects[lot_defects["defect_type"] == "bridge"]["count"].sum())
    insufficient_fill_count = int(lot_defects[lot_defects["defect_type"] == "insufficient_fill"]["count"].sum())

    thermal_pass = (
        max_ramp is not None
        and max_ramp <= limits["max_preheat_ramp_c_per_s"]
        and entry_temp is not None
        and limits["entry_temp_min_c"] <= entry_temp <= limits["entry_temp_max_c"]
        and contact_time_s is not None
        and limits["contact_time_min_s"] <= contact_time_s <= limits["contact_time_max_s"]
    )
    speed_pass = (
        actual_speed is not None
        and limits["speed_min_cm_min"] <= actual_speed <= limits["speed_max_cm_min"]
    )
    defect_pass = bridge_count == 0 and insufficient_fill_count == 0

    failures: List[str] = []
    if max_ramp is None or max_ramp > limits["max_preheat_ramp_c_per_s"]:
        failures.append("preheat_ramp_exceeds_limit")
    if entry_temp is None or not (limits["entry_temp_min_c"] <= entry_temp <= limits["entry_temp_max_c"]):
        failures.append("entry_temp_out_of_window")
    if contact_time_s is None or not (limits["contact_time_min_s"] <= contact_time_s <= limits["contact_time_max_s"]):
        failures.append("contact_time_out_of_window")
    if actual_speed is None or not (limits["speed_min_cm_min"] <= actual_speed <= limits["speed_max_cm_min"]):
        failures.append("speed_out_of_window")
    if bridge_count > 0:
        failures.append("bridging_present")
    if insufficient_fill_count > 0:
        failures.append("insufficient_fill_present")

    lot_rows.append(
        {
            "lot_id": lot_id,
            "profile_id": str(lot["profile_id"]),
            "entry_sensor_id": entry_sensor_id,
            "contact_sensor_id": contact_sensor_id,
            "max_preheat_ramp_c_per_s": max_ramp,
            "board_entry_temp_c": entry_temp,
            "contact_time_s": contact_time_s,
            "actual_speed_cm_min": actual_speed,
            "bridge_count": bridge_count,
            "insufficient_fill_count": insufficient_fill_count,
            "thermal_status": "pass" if thermal_pass else "fail",
            "speed_status": "pass" if speed_pass else "fail",
            "defect_status": "pass" if defect_pass else "fail",
            "audit_status": "pass" if thermal_pass and speed_pass and defect_pass else "fail",
            "failure_reasons": sorted_failure_reasons(failures),
        }
    )

lot_rows.sort(key=lambda row: row["lot_id"])
qualified_lot_ids = [row["lot_id"] for row in lot_rows if row["audit_status"] == "pass"]
blocked_lot_ids = [row["lot_id"] for row in lot_rows if row["audit_status"] == "fail"]

recommended_profiles: List[Dict[str, Any]] = []
for profile_id, group in lots.groupby("profile_id", sort=False):
    matching_rows = [row for row in lot_rows if row["profile_id"] == str(profile_id) and row["audit_status"] == "pass"]
    if not matching_rows:
        continue
    qualified_ids = sorted(row["lot_id"] for row in matching_rows)
    average_entry = round2(sum(float(row["board_entry_temp_c"]) for row in matching_rows) / len(matching_rows))
    average_contact = round2(sum(float(row["contact_time_s"]) for row in matching_rows) / len(matching_rows))
    average_speed = round2(sum(float(row["actual_speed_cm_min"]) for row in matching_rows) / len(matching_rows))
    manifest_row = group.iloc[0]
    recommended_profiles.append(
        {
            "profile_id": str(profile_id),
            "preheater_top_sp_c": round2(float(manifest_row["preheater_top_sp_c"])),
            "chip_wave_height_mm": round2(float(manifest_row["chip_wave_height_mm"])),
            "lambda_wave_height_mm": round2(float(manifest_row["lambda_wave_height_mm"])),
            "lot_count": len(matching_rows),
            "qualified_lot_ids": qualified_ids,
            "average_entry_temp_c": average_entry,
            "average_contact_time_s": average_contact,
            "average_speed_cm_min": average_speed,
            "recommended_speed_cm_min": average_speed,
        }
    )

recommended_profiles.sort(
    key=lambda row: (
        -int(row["lot_count"]),
        abs(float(row["average_entry_temp_c"]) - limits["target_entry_temp_c"]),
        abs(float(row["average_contact_time_s"]) - limits["target_contact_time_s"]),
        abs(float(row["average_speed_cm_min"]) - limits["target_speed_cm_min"]),
        row["profile_id"],
    )
)

output = {
    "line_id": str(lots.iloc[0]["line_id"]),
    "handbook_limits": {
        **{key: round2(value) for key, value in limits.items()},
        "entry_sensor_rule": "lowest_entry_temp_then_smallest_tc_id",
        "contact_sensor_rule": "longest_time_above_threshold_then_smallest_tc_id",
    },
    "qualified_lot_ids": qualified_lot_ids,
    "blocked_lot_ids": blocked_lot_ids,
    "best_profile_id": recommended_profiles[0]["profile_id"] if recommended_profiles else None,
    "lots": lot_rows,
    "recommended_profiles": recommended_profiles,
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    yaml.safe_dump(output, handle, sort_keys=False, allow_unicode=True)
PY
