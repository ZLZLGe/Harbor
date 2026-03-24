from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest


ROOT_DIR = Path(os.environ.get("ROOT_DIR", "/root"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT_DIR / "data")))
RESULT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "battery_policy_frontier.csv")))
REGISTRY_PATH = DATA_DIR / "policy_registry.csv"
TRIALS_PATH = DATA_DIR / "cycling_trial_summaries.jsonl"
REQUIRED_TEMPERATURES = [10, 25, 40]
EXPECTED_COLUMNS = [
    "recovered_capacity_pct",
    "degradation_rate_pct_per_100_cycles",
    "policy_id",
    "charger_family",
    "peak_c_rate",
    "taper_soc",
    "rest_minutes",
]


def load_valid_trials() -> pd.DataFrame:
    rows = []
    with TRIALS_PATH.open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["status"] != "accepted" or int(row["cycles_completed"]) < 180:
                continue
            reference_capacity = float(row["reference_capacity_mah"])
            cycles_completed = float(row["cycles_completed"])
            row["trial_recovered_capacity_pct"] = 100.0 * float(row["recovered_capacity_mah"]) / reference_capacity
            row["trial_degradation_rate_pct_per_100_cycles"] = (
                100.0 * (float(row["capacity_loss_mah"]) / reference_capacity) * (100.0 / cycles_completed)
            )
            rows.append(row)
    return pd.DataFrame(rows)


def compute_expected_frontier() -> pd.DataFrame:
    registry = pd.read_csv(REGISTRY_PATH)
    trials = load_valid_trials()

    temperature_summary = (
        trials.groupby(["policy_id", "temperature_c"], as_index=False)
        .agg(
            trial_count=("replicate_id", "count"),
            recovered_capacity_pct=("trial_recovered_capacity_pct", "mean"),
            degradation_rate_pct_per_100_cycles=("trial_degradation_rate_pct_per_100_cycles", "mean"),
        )
    )
    temperature_summary = temperature_summary[temperature_summary["trial_count"] >= 2].copy()

    policy_rows = []
    for policy_id, group in temperature_summary.groupby("policy_id", sort=False):
        if sorted(group["temperature_c"].tolist()) != REQUIRED_TEMPERATURES:
            continue
        recovered_capacity_pct = float(group["recovered_capacity_pct"].mean())
        degradation_rate_pct_per_100_cycles = float(group["degradation_rate_pct_per_100_cycles"].mean())
        if recovered_capacity_pct < 92.0:
            continue
        policy_rows.append(
            {
                "policy_id": policy_id,
                "recovered_capacity_pct": recovered_capacity_pct,
                "degradation_rate_pct_per_100_cycles": degradation_rate_pct_per_100_cycles,
            }
        )

    best_by_pair = {}
    for row in policy_rows:
        pair = (
            round(row["recovered_capacity_pct"], 2),
            round(row["degradation_rate_pct_per_100_cycles"], 2),
        )
        current = best_by_pair.get(pair)
        if current is None or row["policy_id"] < current["policy_id"]:
            best_by_pair[pair] = row

    deduped_rows = list(best_by_pair.values())

    frontier_rows = []
    for index, row in enumerate(deduped_rows):
        dominated = False
        for other_index, other in enumerate(deduped_rows):
            if index == other_index:
                continue
            if (
                other["recovered_capacity_pct"] >= row["recovered_capacity_pct"]
                and other["degradation_rate_pct_per_100_cycles"] <= row["degradation_rate_pct_per_100_cycles"]
                and (
                    other["recovered_capacity_pct"] > row["recovered_capacity_pct"]
                    or other["degradation_rate_pct_per_100_cycles"] < row["degradation_rate_pct_per_100_cycles"]
                )
            ):
                dominated = True
                break
        if not dominated:
            frontier_rows.append(row)

    expected = pd.DataFrame(frontier_rows).merge(registry, on="policy_id", how="inner", validate="one_to_one")
    expected["recovered_capacity_pct"] = expected["recovered_capacity_pct"].round(2)
    expected["degradation_rate_pct_per_100_cycles"] = expected["degradation_rate_pct_per_100_cycles"].round(2)
    expected["taper_soc"] = expected["taper_soc"].astype(int)
    expected["rest_minutes"] = expected["rest_minutes"].astype(int)
    expected = expected.sort_values(
        by=[
            "recovered_capacity_pct",
            "degradation_rate_pct_per_100_cycles",
            "policy_id",
            "charger_family",
            "peak_c_rate",
            "taper_soc",
            "rest_minutes",
        ],
        ascending=[False, True, True, True, True, True, True],
    ).reset_index(drop=True)
    return expected[EXPECTED_COLUMNS]


@pytest.fixture(scope="module")
def result_df() -> pd.DataFrame:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


def test_result_exists() -> None:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"


def test_columns_and_order(result_df: pd.DataFrame) -> None:
    assert list(result_df.columns) == EXPECTED_COLUMNS


def test_exact_frontier_matches_expected(result_df: pd.DataFrame) -> None:
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
            "recovered_capacity_pct",
            "degradation_rate_pct_per_100_cycles",
            "policy_id",
            "charger_family",
            "peak_c_rate",
            "taper_soc",
            "rest_minutes",
        ],
        ascending=[False, True, True, True, True, True, True],
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(result_df.reset_index(drop=True), sorted_df)


def test_rows_are_non_dominated(result_df: pd.DataFrame) -> None:
    rows = result_df.to_dict("records")
    for index, row in enumerate(rows):
        for other_index, other in enumerate(rows):
            if index == other_index:
                continue
            assert not (
                other["recovered_capacity_pct"] >= row["recovered_capacity_pct"]
                and other["degradation_rate_pct_per_100_cycles"] <= row["degradation_rate_pct_per_100_cycles"]
                and (
                    other["recovered_capacity_pct"] > row["recovered_capacity_pct"]
                    or other["degradation_rate_pct_per_100_cycles"] < row["degradation_rate_pct_per_100_cycles"]
                )
            ), f"row {index} is dominated by row {other_index}"


def test_duplicate_objective_tie_pruning_applied(result_df: pd.DataFrame) -> None:
    policy_ids = set(result_df["policy_id"])
    assert "BAT-BAL-24" in policy_ids
    assert "BAT-BAL-28" not in policy_ids


def test_filtered_policies_are_absent(result_df: pd.DataFrame) -> None:
    excluded = {"BAT-SHIFT-33", "BAT-THERM-08", "BAT-SPARSE-41"}
    assert excluded.isdisjoint(set(result_df["policy_id"]))
