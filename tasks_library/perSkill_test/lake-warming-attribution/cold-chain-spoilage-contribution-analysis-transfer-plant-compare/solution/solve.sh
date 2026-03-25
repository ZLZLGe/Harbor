#!/bin/bash
set -euo pipefail

python3 <<'PY'
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path("/root/data")
OUTPUT_PATH = Path("/root/output/plant_spoilage_driver_comparison.csv")

GROUPS = {
    "TemperatureDiscipline": ["DoorOpenMinutesPerPallet", "SetpointDeviationC"],
    "OperationsPressure": ["RushOrdersPct", "OvertimeHours"],
    "InventoryAging": ["AverageDaysInStorage", "NearExpirySharePct"],
    "EquipmentReliability": ["UnplannedDowntimeHours", "SensorAlarmRatePct"],
}
PLANTS = ["NorthDock", "SouthHub"]


def varimax(loadings: np.ndarray, gamma: float = 1.0, iterations: int = 50, tol: float = 1e-6):
    rows, columns = loadings.shape
    rotation = np.eye(columns)
    previous = 0.0
    for _ in range(iterations):
        rotated = loadings @ rotation
        u, singular_values, vh = np.linalg.svd(
            loadings.T
            @ (rotated**3 - (gamma / rows) * rotated @ np.diag(np.diag(rotated.T @ rotated))),
            full_matrices=False,
        )
        rotation = u @ vh
        current = singular_values.sum()
        if previous and current / previous < 1.0 + tol:
            break
        previous = current
    return loadings @ rotation


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


def analyze_plant(df: pd.DataFrame) -> dict:
    feature_columns = [column for columns in GROUPS.values() for column in columns]
    X = df[feature_columns].to_numpy(dtype=float)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=0)
    y = df["SpoilageLossPct"].to_numpy(dtype=float)

    _, singular_values, vt = np.linalg.svd(X, full_matrices=False)
    raw_loadings = vt[:4].T * singular_values[:4] / np.sqrt(len(df) - 1)
    rotated_loadings = varimax(raw_loadings)
    rotated_scores = X @ np.linalg.pinv(rotated_loadings.T)

    loadings_df = pd.DataFrame(
        rotated_loadings,
        index=feature_columns,
        columns=[f"Factor{i}" for i in range(1, 5)],
    )

    strength = np.zeros((4, 4), dtype=float)
    for group_index, (_, columns) in enumerate(GROUPS.items()):
        for factor_index, factor_name in enumerate(loadings_df.columns):
            strength[group_index, factor_index] = loadings_df.loc[columns, factor_name].abs().sum()

    best_assignment = None
    best_strength = -1.0
    for assignment in permutations(range(4)):
        total_strength = sum(strength[group_index, assignment[group_index]] for group_index in range(4))
        if total_strength > best_strength:
            best_strength = total_strength
            best_assignment = assignment

    ordered_scores = np.column_stack([rotated_scores[:, best_assignment[group_index]] for group_index in range(4)])
    full_r2 = calc_r2(ordered_scores, y)

    decreases = {}
    for group_index, group_name in enumerate(GROUPS):
        keep_columns = [index for index in range(4) if index != group_index]
        reduced_r2 = calc_r2(ordered_scores[:, keep_columns], y)
        decreases[group_name] = max(0.0, full_r2 - reduced_r2)

    total_positive_decrease = sum(decreases.values())
    normalized = {
        group_name: round(decrease / total_positive_decrease * 100.0, 1)
        for group_name, decrease in decreases.items()
    }
    ranking = sorted(normalized.items(), key=lambda item: (-item[1], item[0]))

    return {
        "dominant_driver_category": ranking[0][0],
        "dominant_contribution_pct": ranking[0][1],
        "lead_over_runner_up_pct": round(ranking[0][1] - ranking[1][1], 1),
    }


def main():
    spoilage = pd.read_csv(DATA_DIR / "spoilage_observed_monthly.csv")
    temperature = pd.read_csv(DATA_DIR / "temperature_discipline_monthly.csv")
    operations = pd.read_csv(DATA_DIR / "operations_pressure_monthly.csv")
    inventory = pd.read_csv(DATA_DIR / "inventory_aging_monthly.csv")
    equipment = pd.read_csv(DATA_DIR / "equipment_reliability_monthly.csv")

    merged = (
        spoilage.merge(temperature, on=["PlantCode", "Month"])
        .merge(operations, on=["PlantCode", "Month"])
        .merge(inventory, on=["PlantCode", "Month"])
        .merge(equipment, on=["PlantCode", "Month"])
        .sort_values(["PlantCode", "Month"])
        .reset_index(drop=True)
    )

    rows = []
    for plant_code in PLANTS:
        plant_df = merged[merged["PlantCode"] == plant_code].reset_index(drop=True)
        result = analyze_plant(plant_df)
        rows.append({"plant_code": plant_code, **result})

    output = pd.DataFrame(rows).sort_values("plant_code").reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
PY
