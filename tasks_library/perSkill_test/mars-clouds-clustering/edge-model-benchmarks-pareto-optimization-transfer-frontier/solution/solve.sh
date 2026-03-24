#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
from pathlib import Path

import pandas as pd


REQUIRED_DATASETS = ["road_signs", "shelf_labels", "fruit_sorting"]
OUTPUT_COLUMNS = [
    "validation_accuracy",
    "mean_latency_ms",
    "model_name",
    "runtime",
    "precision",
    "input_resolution",
]


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    kept_rows = []
    for idx, row in df.iterrows():
        dominated = False
        for other_idx, other in df.iterrows():
            if idx == other_idx:
                continue
            if (
                other["validation_accuracy"] >= row["validation_accuracy"]
                and other["mean_latency_ms"] <= row["mean_latency_ms"]
                and (
                    other["validation_accuracy"] > row["validation_accuracy"]
                    or other["mean_latency_ms"] < row["mean_latency_ms"]
                )
            ):
                dominated = True
                break
        if not dominated:
            kept_rows.append(row)
    return pd.DataFrame(kept_rows)


validation = pd.read_csv("/root/data/validation_runs.csv")
validation = validation[validation["status"] == "ok"].copy()

best_per_dataset = (
    validation.groupby(
        [
            "config_id",
            "model_name",
            "runtime",
            "precision",
            "input_resolution",
            "dataset",
        ],
        as_index=False,
    )["top1_accuracy"]
    .max()
)

validation_wide = (
    best_per_dataset.pivot_table(
        index=[
            "config_id",
            "model_name",
            "runtime",
            "precision",
            "input_resolution",
        ],
        columns="dataset",
        values="top1_accuracy",
        aggfunc="max",
    )
    .reset_index()
)

validation_wide = validation_wide.dropna(subset=REQUIRED_DATASETS)
validation_wide["validation_accuracy"] = validation_wide[REQUIRED_DATASETS].mean(axis=1)
validation_wide = validation_wide[validation_wide["validation_accuracy"] >= 0.9000].copy()

latency = pd.read_json("/root/data/latency_runs.jsonl", lines=True)
latency = latency[
    (latency["device"] == "orin-nano")
    & (latency["power_mode"] == "15W")
    & (latency["batch_size"] == 1)
    & (latency["phase"] == "timed")
    & (latency["status"] == "ok")
    & (~latency["warmup"])
].copy()

latency_summary = (
    latency.groupby("config_id", as_index=False)
    .agg(mean_latency_ms=("latency_ms", "mean"), trial_count=("trial", "count"))
)
latency_summary = latency_summary[latency_summary["trial_count"] >= 3][
    ["config_id", "mean_latency_ms"]
]

merged = validation_wide.merge(latency_summary, on="config_id", how="inner")
frontier = pareto_frontier(
    merged[
        [
            "config_id",
            "model_name",
            "runtime",
            "precision",
            "input_resolution",
            "validation_accuracy",
            "mean_latency_ms",
        ]
    ]
)

frontier = frontier.sort_values(
    by=[
        "validation_accuracy",
        "mean_latency_ms",
        "model_name",
        "runtime",
        "precision",
        "input_resolution",
    ],
    ascending=[False, True, True, True, True, True],
).copy()

frontier["validation_accuracy"] = frontier["validation_accuracy"].round(4)
frontier["mean_latency_ms"] = frontier["mean_latency_ms"].round(2)
frontier["input_resolution"] = frontier["input_resolution"].astype(int)

frontier[OUTPUT_COLUMNS].to_csv(Path("/root/edge_model_frontier.csv"), index=False)
PY
