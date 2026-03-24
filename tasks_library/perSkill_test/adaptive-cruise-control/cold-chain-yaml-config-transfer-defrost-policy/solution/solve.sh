#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"

cat <<'PY' > "${TASK_ROOT}/policy_transfer.py"
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import yaml


def load_policy(policy_path: str | Path) -> dict:
    with open(policy_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_group_lookup(policy: dict) -> tuple[dict, list[str]]:
    freezer_to_group = {}
    freezer_order = []
    for group_name, group_cfg in policy["equipment_groups"].items():
        for freezer_id in group_cfg["freezer_ids"]:
            freezer_to_group[freezer_id] = group_name
            freezer_order.append(freezer_id)
    return freezer_to_group, freezer_order


def pick_window(timestamp, windows: dict) -> str:
    current = timestamp.strftime("%H:%M")
    for name, spec in windows.items():
        start = spec["start"]
        end = spec["end"]
        if start <= end:
            if start <= current <= end:
                return name
        else:
            if current >= start or current <= end:
                return name
    raise ValueError(f"no window for {current}")


def unique_codes_in_order(values) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def build_defrost_policy(policy_path, log_path):
    policy = load_policy(policy_path)
    freezer_to_group, freezer_order = build_group_lookup(policy)

    log = pd.read_csv(log_path)
    log["timestamp"] = pd.to_datetime(log["timestamp"])
    log["alarm_code"] = log["alarm_code"].fillna("")

    sample_hours = policy["analysis"]["sample_interval_hours"]
    windows = policy["alarm_windows"]
    summary_rows = []
    recommendations = {}

    for freezer_id in freezer_order:
        group_name = freezer_to_group[freezer_id]
        group_cfg = policy["equipment_groups"][group_name]
        max_temp_c = group_cfg["max_temp_c"]

        freezer_log = log[log["freezer_id"] == freezer_id].sort_values("timestamp").copy()
        freezer_log["is_anomaly"] = (freezer_log["temp_c"] > max_temp_c) | (
            freezer_log["alarm_code"] == "HIGH_TEMP"
        )
        anomaly_rows = freezer_log[freezer_log["is_anomaly"]].copy()

        periods = []
        current_period = []
        previous_ts = None
        for row in anomaly_rows.itertuples(index=False):
            if not current_period:
                current_period = [row]
            elif row.timestamp - previous_ts == pd.Timedelta(hours=sample_hours):
                current_period.append(row)
            else:
                periods.append(current_period)
                current_period = [row]
            previous_ts = row.timestamp
        if current_period:
            periods.append(current_period)

        total_anomaly_hours = int(len(anomaly_rows) * sample_hours)
        door_open_hours = int((anomaly_rows["door_open"] == "Y").sum() * sample_hours)
        peak_temp_c = round(float(anomaly_rows["temp_c"].max()), 1)
        peak_excursion_c = round(max(0.0, peak_temp_c - max_temp_c), 1)

        counts_by_window = {name: 0 for name in windows}
        for row in anomaly_rows.itertuples(index=False):
            counts_by_window[pick_window(row.timestamp, windows)] += 1
        preferred_window = max(windows, key=lambda name: counts_by_window[name])

        analysis_cfg = policy["analysis"]
        if peak_excursion_c >= analysis_cfg["severe_excursion_delta_c"]:
            interval_reduction = 2
        elif total_anomaly_hours >= analysis_cfg["long_event_hours"]:
            interval_reduction = 2
        elif len(periods) >= analysis_cfg["repeat_event_threshold"]:
            interval_reduction = 1
        else:
            interval_reduction = 0

        duration_increase = 0
        if total_anomaly_hours >= analysis_cfg["long_event_hours"]:
            duration_increase += 5
        if door_open_hours >= analysis_cfg["door_open_extension_threshold"]:
            duration_increase += 5
        if peak_excursion_c >= analysis_cfg["severe_excursion_delta_c"]:
            duration_increase += 5

        defrost_cfg = group_cfg["defrost"]
        interval_hours = max(
            defrost_cfg["min_interval_hours"],
            defrost_cfg["base_interval_hours"] - interval_reduction,
        )
        duration_minutes = min(
            defrost_cfg["max_duration_minutes"],
            defrost_cfg["base_duration_minutes"] + duration_increase,
        )

        if peak_excursion_c >= analysis_cfg["severe_excursion_delta_c"]:
            priority = "urgent"
        elif len(periods) >= analysis_cfg["repeat_event_threshold"] or total_anomaly_hours >= analysis_cfg["long_event_hours"]:
            priority = "review"
        else:
            priority = "routine"

        recommendations[freezer_id] = {
            "group": group_name,
            "schedule": {
                "interval_hours": int(interval_hours),
                "duration_minutes": int(duration_minutes),
                "preferred_window": preferred_window,
                "recommended_start": windows[preferred_window]["recommended_start"],
            },
            "analysis": {
                "anomaly_periods": len(periods),
                "total_anomaly_hours": total_anomaly_hours,
                "peak_temp_c": peak_temp_c,
                "peak_excursion_c": peak_excursion_c,
                "door_open_hours": door_open_hours,
                "inspection_priority": priority,
                "trigger_codes": unique_codes_in_order(freezer_log["alarm_code"].tolist()),
            },
        }

        for period in periods:
            start_time = period[0].timestamp
            summary_rows.append(
                {
                    "freezer_id": freezer_id,
                    "group_name": group_name,
                    "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end_time": period[-1].timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "duration_hours": len(period),
                    "peak_temp_c": round(float(max(item.temp_c for item in period)), 1),
                    "door_open_hours": sum(1 for item in period if item.door_open == "Y"),
                    "window_name": pick_window(start_time, windows),
                    "priority": priority,
                }
            )

    policy_output = {
        "site": policy["site"],
        "source_files": {
            "policy": "freezer_policy.yaml",
            "log": "temperature_log.csv",
        },
        "policy_recommendations": recommendations,
    }
    return policy_output, summary_rows


def main() -> None:
    root = Path(__file__).resolve().parent
    policy_output, summary_rows = build_defrost_policy(
        root / "freezer_policy.yaml",
        root / "temperature_log.csv",
    )

    with open(root / "defrost_policy.yaml", "w", encoding="utf-8") as handle:
        yaml.safe_dump(policy_output, handle, sort_keys=False, allow_unicode=True)

    fieldnames = [
        "freezer_id",
        "group_name",
        "start_time",
        "end_time",
        "duration_hours",
        "peak_temp_c",
        "door_open_hours",
        "window_name",
        "priority",
    ]
    with open(root / "anomaly_summary.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
PY

python3 "${TASK_ROOT}/policy_transfer.py"
