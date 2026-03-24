#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import pandas as pd
import yaml


def detect_paths():
    root = Path("/root")
    try:
        if (root / "pressure_review.yaml").exists():
            return root, root, root / "pressure_surge_metrics.csv"
    except PermissionError:
        pass
    task_root = Path.cwd().parent
    return task_root, task_root / "environment", task_root / "pressure_surge_metrics.csv"


ROOT, INPUT_ROOT, OUTPUT_PATH = detect_paths()
CONFIG_PATH = INPUT_ROOT / "pressure_review.yaml"
LOGS_DIR = INPUT_ROOT / "pressure_runs"


def in_window(df, bounds):
    start, end = bounds
    return df[(df["time_s"] >= start) & (df["time_s"] <= end)].reset_index(drop=True)


def round2(value):
    return round(float(value), 2)


def compute_metrics(df, config):
    evaluation = in_window(df, config["evaluation_window_s"])
    dip_window = in_window(df, config["dip_search_window_s"])
    steady = in_window(df, config["steady_state_window_s"])

    dip_index = dip_window["discharge_pressure_bar"].idxmin()
    minimum_pressure = float(dip_window.loc[dip_index, "discharge_pressure_bar"])
    minimum_time = float(dip_window.loc[dip_index, "time_s"])

    recovery = evaluation[evaluation["time_s"] >= minimum_time].reset_index(drop=True)
    recovery_span = float(config["target_pressure_bar"]) - minimum_pressure
    low_mark = minimum_pressure + 0.1 * recovery_span
    high_mark = minimum_pressure + 0.9 * recovery_span

    t10 = float(recovery[recovery["discharge_pressure_bar"] >= low_mark]["time_s"].iloc[0])
    t90 = float(recovery[recovery["discharge_pressure_bar"] >= high_mark]["time_s"].iloc[0])

    metrics = {
        "rise_time_s": round2(t90 - t10),
        "overshoot_pct": round2(
            max(
                0.0,
                (float(evaluation["discharge_pressure_bar"].max()) - float(config["target_pressure_bar"]))
                / float(config["target_pressure_bar"])
                * 100.0,
            )
        ),
        "steady_state_error_bar": round2(
            abs(float(steady["discharge_pressure_bar"].mean()) - float(config["target_pressure_bar"]))
        ),
        "low_pressure_duration_s": round2(
            float((evaluation["discharge_pressure_bar"] < float(config["low_pressure_threshold_bar"])).sum())
            * float(config["sample_period_s"])
        ),
    }

    pass_count = sum(
        [
            metrics["rise_time_s"] <= float(config["limits"]["rise_time_s_max"]),
            metrics["overshoot_pct"] <= float(config["limits"]["overshoot_pct_max"]),
            metrics["steady_state_error_bar"] <= float(config["limits"]["steady_state_error_bar_max"]),
            metrics["low_pressure_duration_s"] <= float(config["limits"]["low_pressure_duration_s_max"]),
        ]
    )
    metrics["pass_count"] = int(pass_count)
    return metrics


with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

rows = []
for candidate in config["candidates"]:
    df = pd.read_csv(LOGS_DIR / f"{candidate}.csv")
    metrics = compute_metrics(df, config)
    rows.append(
        {
            "candidate": candidate,
            "rise_time_s": metrics["rise_time_s"],
            "overshoot_pct": metrics["overshoot_pct"],
            "steady_state_error_bar": metrics["steady_state_error_bar"],
            "low_pressure_duration_s": metrics["low_pressure_duration_s"],
            "thresholds_passed": f"{metrics['pass_count']}/4",
            "_pass_count": metrics["pass_count"],
        }
    )

rows.sort(
    key=lambda row: (
        -row["_pass_count"],
        row["low_pressure_duration_s"],
        row["steady_state_error_bar"],
        row["overshoot_pct"],
        row["candidate"],
    )
)

for rank, row in enumerate(rows, start=1):
    row["rank"] = rank

output = pd.DataFrame(
    [
        {
            "rank": row["rank"],
            "candidate": row["candidate"],
            "rise_time_s": row["rise_time_s"],
            "overshoot_pct": row["overshoot_pct"],
            "steady_state_error_bar": row["steady_state_error_bar"],
            "low_pressure_duration_s": row["low_pressure_duration_s"],
            "thresholds_passed": row["thresholds_passed"],
        }
        for row in rows
    ]
)

output.to_csv(OUTPUT_PATH, index=False, float_format="%.2f")
PY
