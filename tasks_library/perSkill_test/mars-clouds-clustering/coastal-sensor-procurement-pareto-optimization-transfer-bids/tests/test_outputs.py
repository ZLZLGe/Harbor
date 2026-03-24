from pathlib import Path
import os

import pandas as pd
import pytest


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT_DIR / "data")))
RESULT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "procurement_frontier.csv")))
COMPONENTS_PATH = DATA_DIR / "bundle_components.csv"
OPERATIONS_PATH = DATA_DIR / "bundle_operations.csv"
EXPECTED_COLUMNS = [
    "expected_annual_coverage_km",
    "total_3yr_cost_usd",
    "bundle_id",
    "vendor",
    "buoy_model",
    "sensor_suite",
]


def compute_expected_frontier() -> pd.DataFrame:
    components = pd.read_csv(COMPONENTS_PATH)
    operations = pd.read_csv(OPERATIONS_PATH)

    components["line_cost_usd"] = components["quantity"] * components["unit_cost_usd"]
    capex = (
        components.groupby(["bundle_id", "vendor", "buoy_model", "sensor_suite"], as_index=False)["line_cost_usd"]
        .sum()
        .rename(columns={"line_cost_usd": "procurement_capex_usd"})
    )

    bundles = capex.merge(operations, on="bundle_id", how="inner", validate="one_to_one")
    bundles["expected_annual_coverage_km"] = (
        bundles["shoreline_km"] * bundles["uptime_rate"] * bundles["data_return_rate"]
    )
    bundles = bundles[bundles["expected_annual_coverage_km"] >= 170].copy()
    bundles["total_3yr_cost_usd"] = (
        bundles["procurement_capex_usd"]
        + 3 * (bundles["annual_support_usd"] + bundles["annual_permit_usd"])
        + bundles["replacement_events_3yr"] * bundles["replacement_cost_usd"]
    )

    rows = bundles.to_dict("records")
    keep_mask = []
    for row in rows:
        dominated = False
        for other in rows:
            if other["bundle_id"] == row["bundle_id"]:
                continue
            if (
                other["expected_annual_coverage_km"] >= row["expected_annual_coverage_km"]
                and other["total_3yr_cost_usd"] <= row["total_3yr_cost_usd"]
                and (
                    other["expected_annual_coverage_km"] > row["expected_annual_coverage_km"]
                    or other["total_3yr_cost_usd"] < row["total_3yr_cost_usd"]
                )
            ):
                dominated = True
                break
        keep_mask.append(not dominated)

    expected = bundles.loc[keep_mask, EXPECTED_COLUMNS].copy()
    expected["expected_annual_coverage_km"] = expected["expected_annual_coverage_km"].round(2)
    expected["total_3yr_cost_usd"] = expected["total_3yr_cost_usd"].round(2)
    expected = expected.sort_values(
        by=[
            "expected_annual_coverage_km",
            "total_3yr_cost_usd",
            "bundle_id",
            "vendor",
            "buoy_model",
            "sensor_suite",
        ],
        ascending=[False, True, True, True, True, True],
    ).reset_index(drop=True)
    return expected


@pytest.fixture(scope="module")
def result_df() -> pd.DataFrame:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


def test_result_exists() -> None:
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"


def test_columns_and_order(result_df: pd.DataFrame) -> None:
    assert list(result_df.columns) == EXPECTED_COLUMNS


def test_frontier_not_empty(result_df: pd.DataFrame) -> None:
    assert len(result_df) > 0


def test_rows_meet_threshold_and_rounding(result_df: pd.DataFrame) -> None:
    assert (result_df["expected_annual_coverage_km"] >= 170).all()
    assert result_df["expected_annual_coverage_km"].map(lambda value: round(value, 2) == value).all()
    assert result_df["total_3yr_cost_usd"].map(lambda value: round(value, 2) == value).all()


def test_rows_sorted(result_df: pd.DataFrame) -> None:
    sorted_df = result_df.sort_values(
        by=[
            "expected_annual_coverage_km",
            "total_3yr_cost_usd",
            "bundle_id",
            "vendor",
            "buoy_model",
            "sensor_suite",
        ],
        ascending=[False, True, True, True, True, True],
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(result_df.reset_index(drop=True), sorted_df)


def test_rows_are_non_dominated(result_df: pd.DataFrame) -> None:
    records = result_df.to_dict("records")
    for index, row in enumerate(records):
        for other_index, other in enumerate(records):
            if index == other_index:
                continue
            assert not (
                other["expected_annual_coverage_km"] >= row["expected_annual_coverage_km"]
                and other["total_3yr_cost_usd"] <= row["total_3yr_cost_usd"]
                and (
                    other["expected_annual_coverage_km"] > row["expected_annual_coverage_km"]
                    or other["total_3yr_cost_usd"] < row["total_3yr_cost_usd"]
                )
            ), f"row {index} is dominated by row {other_index}"


def test_matches_expected_frontier(result_df: pd.DataFrame) -> None:
    expected = compute_expected_frontier()
    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True),
        expected,
        check_exact=False,
        atol=1e-9,
        rtol=0.0,
    )


def test_filtered_and_dominated_bundles_absent(result_df: pd.DataFrame) -> None:
    excluded_bundle_ids = {"CB-611", "CB-305", "CB-407"}
    assert excluded_bundle_ids.isdisjoint(set(result_df["bundle_id"]))
