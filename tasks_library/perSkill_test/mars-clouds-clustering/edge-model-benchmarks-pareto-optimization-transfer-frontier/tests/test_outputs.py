from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


RESULT_PATH = Path("/root/edge_model_frontier.csv")
VALIDATION_PATH = Path("/root/data/validation_runs.csv")
LATENCY_PATH = Path("/root/data/latency_runs.jsonl")
REQUIRED_DATASETS = ["road_signs", "shelf_labels", "fruit_sorting"]
EXPECTED_COLUMNS = [
    "validation_accuracy",
    "mean_latency_ms",
    "model_name",
    "runtime",
    "precision",
    "input_resolution",
]


def compute_expected_frontier() -> pd.DataFrame:
    validation = pd.read_csv(VALIDATION_PATH)
    validation = validation[validation["status"] == "ok"].copy()

    grouped = (
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

    accuracy_rows = []
    for keys, group in grouped.groupby(
        ["config_id", "model_name", "runtime", "precision", "input_resolution"],
        sort=False,
    ):
        best_by_dataset = {row["dataset"]: row["top1_accuracy"] for _, row in group.iterrows()}
        if any(dataset not in best_by_dataset for dataset in REQUIRED_DATASETS):
            continue
        validation_accuracy = sum(best_by_dataset[dataset] for dataset in REQUIRED_DATASETS) / len(REQUIRED_DATASETS)
        if validation_accuracy < 0.9000:
            continue
        config_id, model_name, runtime, precision, input_resolution = keys
        accuracy_rows.append(
            {
                "config_id": config_id,
                "model_name": model_name,
                "runtime": runtime,
                "precision": precision,
                "input_resolution": int(input_resolution),
                "validation_accuracy": validation_accuracy,
            }
        )

    latency_samples: dict[str, list[float]] = {}
    with LATENCY_PATH.open() as handle:
        for line in handle:
            row = json.loads(line)
            if (
                row["device"] == "orin-nano"
                and row["power_mode"] == "15W"
                and row["batch_size"] == 1
                and row["phase"] == "timed"
                and row["status"] == "ok"
                and row["warmup"] is False
            ):
                latency_samples.setdefault(row["config_id"], []).append(float(row["latency_ms"]))

    latency_rows = {
        config_id: sum(samples) / len(samples)
        for config_id, samples in latency_samples.items()
        if len(samples) >= 3
    }

    joined_rows = []
    for row in accuracy_rows:
        latency_value = latency_rows.get(row["config_id"])
        if latency_value is None:
            continue
        joined_rows.append(
            {
                "validation_accuracy": row["validation_accuracy"],
                "mean_latency_ms": latency_value,
                "model_name": row["model_name"],
                "runtime": row["runtime"],
                "precision": row["precision"],
                "input_resolution": row["input_resolution"],
            }
        )

    frontier_rows = []
    for idx, row in enumerate(joined_rows):
        dominated = False
        for other_idx, other in enumerate(joined_rows):
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
            frontier_rows.append(row)

    expected = pd.DataFrame(frontier_rows)
    expected["validation_accuracy"] = expected["validation_accuracy"].round(4)
    expected["mean_latency_ms"] = expected["mean_latency_ms"].round(2)
    expected["input_resolution"] = expected["input_resolution"].astype(int)
    expected = expected.sort_values(
        by=[
            "validation_accuracy",
            "mean_latency_ms",
            "model_name",
            "runtime",
            "precision",
            "input_resolution",
        ],
        ascending=[False, True, True, True, True, True],
    ).reset_index(drop=True)
    return expected[EXPECTED_COLUMNS]


@pytest.fixture
def result_df() -> pd.DataFrame:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


def test_result_exists() -> None:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"


def test_columns_and_order(result_df: pd.DataFrame) -> None:
    assert list(result_df.columns) == EXPECTED_COLUMNS


def test_exact_frontier_contents(result_df: pd.DataFrame) -> None:
    expected = compute_expected_frontier()
    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True),
        expected,
        check_exact=False,
        atol=1e-9,
        rtol=0.0,
    )


def test_rows_are_sorted(result_df: pd.DataFrame) -> None:
    sorted_df = result_df.sort_values(
        by=[
            "validation_accuracy",
            "mean_latency_ms",
            "model_name",
            "runtime",
            "precision",
            "input_resolution",
        ],
        ascending=[False, True, True, True, True, True],
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(result_df.reset_index(drop=True), sorted_df)


def test_rows_are_non_dominated(result_df: pd.DataFrame) -> None:
    records = result_df.to_dict("records")
    for idx, row in enumerate(records):
        for other_idx, other in enumerate(records):
            if idx == other_idx:
                continue
            assert not (
                other["validation_accuracy"] >= row["validation_accuracy"]
                and other["mean_latency_ms"] <= row["mean_latency_ms"]
                and (
                    other["validation_accuracy"] > row["validation_accuracy"]
                    or other["mean_latency_ms"] < row["mean_latency_ms"]
                )
            ), f"row {idx} is dominated by row {other_idx}"


def test_excluded_configurations_do_not_leak(result_df: pd.DataFrame) -> None:
    excluded = {"microdet-v2", "fastvit-x", "nanonet-m", "swiftdet-s", "edgevit-mini"}
    assert excluded.isdisjoint(set(result_df["model_name"]))
