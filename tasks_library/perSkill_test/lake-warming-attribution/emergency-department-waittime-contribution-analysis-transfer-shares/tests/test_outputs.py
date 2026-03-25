import csv
import math
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path("/root/output/waittime_driver_shares.csv")
DATA_DIR = Path("/root/data")

GROUPS = {
    "ArrivalPressure": ["ArrivalsPerHour", "HighAcuityPct"],
    "StaffingGap": ["RNHoursGap", "PhysicianGapPct"],
    "Diagnostics": ["MedianLabMinutes", "MedianImagingMinutes"],
    "BedFlow": ["BoardingHoursPerPatient", "BedAssignmentLagMinutes"],
}


def calc_r2(predictors: np.ndarray, response: np.ndarray) -> float:
    predictors = np.asarray(predictors, dtype=float)
    if predictors.ndim == 1:
        predictors = predictors[:, None]
    design = np.column_stack([np.ones(len(predictors)), predictors])
    coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
    fitted = design @ coefficients
    ss_res = np.square(response - fitted).sum()
    ss_tot = np.square(response - response.mean()).sum()
    return 1.0 - ss_res / ss_tot


def expected_rows():
    wait_times = pd.read_csv(DATA_DIR / "ed_wait_times_daily.csv")
    arrivals = pd.read_csv(DATA_DIR / "arrival_pressure_daily.csv")
    staffing = pd.read_csv(DATA_DIR / "staffing_gap_daily.csv")
    diagnostics = pd.read_csv(DATA_DIR / "diagnostics_turnaround_daily.csv")
    bed_flow = pd.read_csv(DATA_DIR / "bed_flow_daily.csv")

    df = (
        wait_times.merge(arrivals, on="VisitDate")
        .merge(staffing, on="VisitDate")
        .merge(diagnostics, on="VisitDate")
        .merge(bed_flow, on="VisitDate")
        .sort_values("VisitDate")
        .reset_index(drop=True)
    )

    feature_columns = [column for columns in GROUPS.values() for column in columns]
    X = df[feature_columns].to_numpy(dtype=float)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=0)
    y = df["AverageWaitMinutes"].to_numpy(dtype=float)

    u, singular_values, vt = np.linalg.svd(X, full_matrices=False)
    scores = u[:, :4] * singular_values[:4]
    loadings = pd.DataFrame(
        vt[:4].T,
        index=feature_columns,
        columns=[f"PC{i}" for i in range(1, 5)],
    )

    strength = np.zeros((4, 4), dtype=float)
    for group_index, (_, columns) in enumerate(GROUPS.items()):
        for component_index, component_name in enumerate(loadings.columns):
            strength[group_index, component_index] = loadings.loc[columns, component_name].abs().sum()

    best_assignment = None
    best_strength = -1.0
    for assignment in permutations(range(4)):
        total_strength = sum(strength[group_index, assignment[group_index]] for group_index in range(4))
        if total_strength > best_strength:
            best_strength = total_strength
            best_assignment = assignment

    ordered_scores = np.column_stack([scores[:, best_assignment[group_index]] for group_index in range(4)])
    full_r2 = calc_r2(ordered_scores, y)

    decreases = {}
    for group_index, group_name in enumerate(GROUPS):
        keep_columns = [index for index in range(4) if index != group_index]
        reduced_r2 = calc_r2(ordered_scores[:, keep_columns], y)
        decreases[group_name] = max(0.0, full_r2 - reduced_r2)

    total_positive_decrease = sum(decreases.values())
    rows = [
        {
            "driver_category": group_name,
            "normalized_contribution_pct": round(decrease / total_positive_decrease * 100.0, 1),
        }
        for group_name, decrease in decreases.items()
    ]
    return sorted(rows, key=lambda row: (-row["normalized_contribution_pct"], row["driver_category"]))


def main():
    assert OUTPUT_PATH.exists(), "waittime_driver_shares.csv not found"

    with OUTPUT_PATH.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == ["driver_category", "normalized_contribution_pct"], "unexpected columns"

    assert len(rows) == 4, "output must contain exactly four rows"

    seen_categories = [row["driver_category"] for row in rows]
    assert set(seen_categories) == set(GROUPS), "output must contain all four driver categories exactly once"
    assert len(seen_categories) == len(set(seen_categories)), "driver categories must not repeat"

    contributions = [float(row["normalized_contribution_pct"]) for row in rows]
    for value in contributions:
        assert 0.0 <= value <= 100.0, "normalized contributions must be between 0 and 100"
        assert math.isclose(value, round(value, 1), abs_tol=1e-9), "values must keep one decimal place"

    assert all(
        contributions[index] >= contributions[index + 1] for index in range(len(contributions) - 1)
    ), "rows must be sorted by contribution descending"
    assert 99.9 <= sum(contributions) <= 100.1, "contributions must sum to approximately 100"

    expected = expected_rows()
    for actual, target in zip(rows, expected):
        assert actual["driver_category"] == target["driver_category"], "driver category ranking is incorrect"
        assert abs(float(actual["normalized_contribution_pct"]) - target["normalized_contribution_pct"]) <= 0.1, (
            "normalized contribution does not match expected value"
        )


if __name__ == "__main__":
    main()
