import json
import os
import re

import numpy as np
import pandas as pd

DATA_FILE = os.environ.get("DATA_FILE", "/root/data/loan_scoring_cases.csv")
REPORT_FILE = os.environ.get("REPORT_FILE", "/root/results/loan_model_audit.md")


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


def compute_expected_summary():
    frame = pd.read_csv(DATA_FILE)
    frame["age_band"] = pd.cut(
        frame["age"],
        bins=[18, 30, 45, float("inf")],
        labels=["18-29", "30-44", "45+"],
        right=False,
    )
    overall_metrics = {
        "roc_auc": roc_auc_score_manual(frame["defaulted"], frame["predicted_default_probability"]),
        "pr_auc": average_precision_manual(frame["defaulted"], frame["predicted_default_probability"]),
        "brier_score": brier_score(frame["defaulted"], frame["predicted_default_probability"]),
    }
    overall_metrics["best_threshold"] = find_best_threshold(frame["defaulted"], frame["predicted_default_probability"])
    age_metrics = compute_slice_metrics(frame, "age_band", ["18-29", "30-44", "45+"], "age_band")
    channel_metrics = compute_slice_metrics(
        frame,
        "acquisition_channel",
        sorted(frame["acquisition_channel"].unique().tolist()),
        "acquisition_channel",
    )
    return {
        "overall_metrics": overall_metrics,
        "confusion_matrix_at_best_threshold": confusion_matrix_counts(
            frame["defaulted"],
            frame["predicted_default_probability"],
            overall_metrics["best_threshold"],
        ),
        "age_band_metrics": age_metrics,
        "channel_metrics": channel_metrics,
        "calibration_findings": {
            "age_band": summarize_calibration(age_metrics, "age_band"),
            "acquisition_channel": summarize_calibration(channel_metrics, "acquisition_channel"),
        },
    }


def assert_close(actual, expected, path):
    if isinstance(expected, bool):
        assert isinstance(actual, bool), f"{path} should be bool"
        assert actual == expected, f"{path}: expected {expected}, got {actual}"
        return
    if isinstance(expected, int):
        assert actual == expected, f"{path}: expected {expected}, got {actual}"
        return
    if isinstance(expected, float):
        assert abs(actual - expected) <= 1e-9, f"{path}: expected {expected}, got {actual}"
        return
    assert actual == expected, f"{path}: expected {expected}, got {actual}"


def extract_summary_json(report_text):
    matches = re.findall(r"```json\s*(.*?)\s*```", report_text, flags=re.DOTALL)
    assert matches, "Missing fenced JSON block"
    return json.loads(matches[-1])


def main():
    assert os.path.exists(REPORT_FILE), f"Missing report: {REPORT_FILE}"

    with open(REPORT_FILE, "r", encoding="utf-8") as handle:
        report_text = handle.read()

    required_headings = [
        "# Loan Risk Model Audit",
        "## Overall Metrics",
        "## Confusion Matrix at Best Threshold",
        "## Slice Performance by Age Band",
        "## Slice Performance by Acquisition Channel",
        "## Calibration Conclusions",
        "## Audit Summary JSON",
    ]
    for heading in required_headings:
        assert heading in report_text, f"Missing heading: {heading}"

    actual = extract_summary_json(report_text)
    expected = compute_expected_summary()

    for key, value in expected["overall_metrics"].items():
        assert_close(actual["overall_metrics"][key], value, f"overall_metrics.{key}")

    for key, value in expected["confusion_matrix_at_best_threshold"].items():
        assert_close(actual["confusion_matrix_at_best_threshold"][key], value, f"confusion_matrix_at_best_threshold.{key}")

    assert [row["age_band"] for row in actual["age_band_metrics"]] == ["18-29", "30-44", "45+"], "Age band order is incorrect"
    assert [row["acquisition_channel"] for row in actual["channel_metrics"]] == ["branch", "organic", "partner"], "Channel order is incorrect"

    for index, expected_row in enumerate(expected["age_band_metrics"]):
        actual_row = actual["age_band_metrics"][index]
        for key, value in expected_row.items():
            assert_close(actual_row[key], value, f"age_band_metrics[{index}].{key}")

    for index, expected_row in enumerate(expected["channel_metrics"]):
        actual_row = actual["channel_metrics"][index]
        for key, value in expected_row.items():
            assert_close(actual_row[key], value, f"channel_metrics[{index}].{key}")

    for dimension, expected_block in expected["calibration_findings"].items():
        actual_block = actual["calibration_findings"][dimension]
        for key, value in expected_block.items():
            assert_close(actual_block[key], value, f"calibration_findings.{dimension}.{key}")
        assert actual_block["most_over_predicted_segment"] in report_text, "Calibration conclusion text should mention the most over-predicted segment"
        assert actual_block["most_under_predicted_segment"] in report_text, "Calibration conclusion text should mention the most under-predicted segment"


if __name__ == "__main__":
    main()
