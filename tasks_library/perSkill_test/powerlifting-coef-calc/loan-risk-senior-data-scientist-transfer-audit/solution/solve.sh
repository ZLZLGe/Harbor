#!/bin/bash

set -euo pipefail

INPUT_PATH="${INPUT_PATH:-/root/data/loan_scoring_cases.csv}"
OUTPUT_PATH="${OUTPUT_PATH:-/root/results/loan_model_audit.md}"

mkdir -p "$(dirname "$OUTPUT_PATH")"
export INPUT_PATH
export OUTPUT_PATH

python3 - <<'PY'
import json
import os

import numpy as np
import pandas as pd

INPUT_PATH = os.environ["INPUT_PATH"]
OUTPUT_PATH = os.environ["OUTPUT_PATH"]


def roc_auc_score_manual(y_true, y_score):
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    positives = y_score[y_true == 1]
    negatives = y_score[y_true == 0]
    wins = 0.0
    for score in positives:
        wins += np.sum(score > negatives)
        wins += 0.5 * np.sum(score == negatives)
    return wins / (len(positives) * len(negatives))


def average_precision_manual(y_true, y_score):
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    order = np.argsort(-y_score, kind="mergesort")
    y_sorted = y_true[order]
    true_positives = np.cumsum(y_sorted == 1)
    false_positives = np.cumsum(y_sorted == 0)
    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / np.sum(y_true == 1)

    average_precision = 0.0
    previous_recall = 0.0
    for precision_value, recall_value, label in zip(precision, recall, y_sorted):
        if label == 1:
            average_precision += precision_value * (recall_value - previous_recall)
            previous_recall = recall_value
    return average_precision


def brier_score(y_true, y_score):
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    return np.mean((y_score - y_true) ** 2)


def find_best_threshold(y_true, y_score):
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    best_threshold = None
    best_j = None
    for threshold in sorted(set(y_score.tolist() + [0.0, 1.0])):
        predicted = (y_score >= threshold).astype(int)
        tp = int(np.sum((predicted == 1) & (y_true == 1)))
        fp = int(np.sum((predicted == 1) & (y_true == 0)))
        fn = int(np.sum((predicted == 0) & (y_true == 1)))
        tn = int(np.sum((predicted == 0) & (y_true == 0)))
        tpr = tp / (tp + fn)
        fpr = fp / (fp + tn)
        j_stat = tpr - fpr
        if best_j is None or j_stat > best_j + 1e-12 or (abs(j_stat - best_j) <= 1e-12 and threshold < best_threshold):
            best_threshold = threshold
            best_j = j_stat
    return best_threshold


def confusion_matrix_counts(y_true, y_score, threshold):
    y_true = np.asarray(y_true, dtype=int)
    predicted = (np.asarray(y_score, dtype=float) >= threshold).astype(int)
    return {
        "true_negative": int(np.sum((y_true == 0) & (predicted == 0))),
        "false_positive": int(np.sum((y_true == 0) & (predicted == 1))),
        "false_negative": int(np.sum((y_true == 1) & (predicted == 0))),
        "true_positive": int(np.sum((y_true == 1) & (predicted == 1))),
    }


def compute_slice_metrics(frame, group_col, ordered_values, output_key):
    rows = []
    for value in ordered_values:
        subset = frame[frame[group_col] == value]
        default_rate = float(subset["defaulted"].mean())
        avg_prediction = float(subset["predicted_default_probability"].mean())
        rows.append(
            {
                output_key: value,
                "count": int(len(subset)),
                "default_rate": default_rate,
                "avg_prediction": avg_prediction,
                "calibration_gap": avg_prediction - default_rate,
                "roc_auc": roc_auc_score_manual(subset["defaulted"], subset["predicted_default_probability"]),
                "pr_auc": average_precision_manual(subset["defaulted"], subset["predicted_default_probability"]),
                "brier_score": brier_score(subset["defaulted"], subset["predicted_default_probability"]),
            }
        )
    return rows


def summarize_calibration(rows, segment_key):
    gaps = {row[segment_key]: row["calibration_gap"] for row in rows}
    most_over = max(gaps, key=gaps.get)
    most_under = min(gaps, key=gaps.get)
    max_abs_gap = max(abs(value) for value in gaps.values())
    return {
        "most_over_predicted_segment": most_over,
        "most_under_predicted_segment": most_under,
        "max_abs_gap": max_abs_gap,
        "material_issue": bool(max_abs_gap > 0.05),
    }


def format_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return f"{value:.6f}"


def markdown_table(columns, rows):
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(format_value(row[column]) for column in columns) + " |")
    return "\n".join([header, separator] + body)


df = pd.read_csv(INPUT_PATH)
df["age_band"] = pd.cut(
    df["age"],
    bins=[18, 30, 45, float("inf")],
    labels=["18-29", "30-44", "45+"],
    right=False,
)

overall_metrics = {
    "roc_auc": roc_auc_score_manual(df["defaulted"], df["predicted_default_probability"]),
    "pr_auc": average_precision_manual(df["defaulted"], df["predicted_default_probability"]),
    "brier_score": brier_score(df["defaulted"], df["predicted_default_probability"]),
}
overall_metrics["best_threshold"] = find_best_threshold(df["defaulted"], df["predicted_default_probability"])

confusion = confusion_matrix_counts(
    df["defaulted"],
    df["predicted_default_probability"],
    overall_metrics["best_threshold"],
)

age_metrics = compute_slice_metrics(df, "age_band", ["18-29", "30-44", "45+"], "age_band")
channel_values = sorted(df["acquisition_channel"].unique().tolist())
channel_metrics = compute_slice_metrics(df, "acquisition_channel", channel_values, "acquisition_channel")

calibration_findings = {
    "age_band": summarize_calibration(age_metrics, "age_band"),
    "acquisition_channel": summarize_calibration(channel_metrics, "acquisition_channel"),
}

summary = {
    "overall_metrics": overall_metrics,
    "confusion_matrix_at_best_threshold": confusion,
    "age_band_metrics": age_metrics,
    "channel_metrics": channel_metrics,
    "calibration_findings": calibration_findings,
}

overall_rows = [
    {"metric": "roc_auc", "value": overall_metrics["roc_auc"]},
    {"metric": "pr_auc", "value": overall_metrics["pr_auc"]},
    {"metric": "brier_score", "value": overall_metrics["brier_score"]},
    {"metric": "best_threshold", "value": overall_metrics["best_threshold"]},
]

confusion_rows = [
    {"metric": "true_negative", "value": confusion["true_negative"]},
    {"metric": "false_positive", "value": confusion["false_positive"]},
    {"metric": "false_negative", "value": confusion["false_negative"]},
    {"metric": "true_positive", "value": confusion["true_positive"]},
]

lines = [
    "# Loan Risk Model Audit",
    "",
    "## Overall Metrics",
    markdown_table(["metric", "value"], overall_rows),
    "",
    "## Confusion Matrix at Best Threshold",
    markdown_table(["metric", "value"], confusion_rows),
    "",
    "## Slice Performance by Age Band",
    markdown_table(
        ["age_band", "count", "default_rate", "avg_prediction", "calibration_gap", "roc_auc", "pr_auc", "brier_score"],
        age_metrics,
    ),
    "",
    "## Slice Performance by Acquisition Channel",
    markdown_table(
        [
            "acquisition_channel",
            "count",
            "default_rate",
            "avg_prediction",
            "calibration_gap",
            "roc_auc",
            "pr_auc",
            "brier_score",
        ],
        channel_metrics,
    ),
    "",
    "## Calibration Conclusions",
    (
        "- Age bands: most over-predicted segment is "
        f"`{calibration_findings['age_band']['most_over_predicted_segment']}`, most under-predicted segment is "
        f"`{calibration_findings['age_band']['most_under_predicted_segment']}`, max_abs_gap is "
        f"{calibration_findings['age_band']['max_abs_gap']:.6f}, material_issue is "
        f"{str(calibration_findings['age_band']['material_issue']).lower()}."
    ),
    (
        "- Acquisition channels: most over-predicted segment is "
        f"`{calibration_findings['acquisition_channel']['most_over_predicted_segment']}`, most under-predicted segment is "
        f"`{calibration_findings['acquisition_channel']['most_under_predicted_segment']}`, max_abs_gap is "
        f"{calibration_findings['acquisition_channel']['max_abs_gap']:.6f}, material_issue is "
        f"{str(calibration_findings['acquisition_channel']['material_issue']).lower()}."
    ),
    "",
    "## Audit Summary JSON",
    "```json",
    json.dumps(summary, ensure_ascii=False, indent=2),
    "```",
]

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
PY
