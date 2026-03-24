#!/bin/bash
set -euo pipefail

export DATA_DIR="${DATA_DIR:-/root/data}"
export OUTPUT_PATH="${OUTPUT_PATH:-/root/gait_protocol_rankings.csv}"

python - <<'PY'
from pathlib import Path
import os

import numpy as np
import pandas as pd

data_dir = Path(os.environ["DATA_DIR"])
output_path = Path(os.environ["OUTPUT_PATH"])

feature_cols = [
    "cadence_spm",
    "stride_time_cv",
    "left_right_asymmetry",
    "knee_flexion_deg",
    "balance_index",
]
scale_map = {
    "cadence_spm": 20.0,
    "stride_time_cv": 8.0,
    "left_right_asymmetry": 0.2,
    "knee_flexion_deg": 20.0,
    "balance_index": 50.0,
}
weight_cols = [
    "cadence_weight",
    "stride_time_cv_weight",
    "left_right_asymmetry_weight",
    "knee_flexion_weight",
    "balance_weight",
]

prototypes = pd.read_csv(data_dir / "gait_prototypes.csv")
validation = pd.read_csv(data_dir / "validation_patients.csv")
query = pd.read_csv(data_dir / "query_patients.csv")
profiles = pd.read_csv(data_dir / "weight_profiles.csv")

scale_vector = np.array([scale_map[col] for col in feature_cols], dtype=float)


def rank_prototypes(patient_row: pd.Series, weights: np.ndarray) -> list[dict]:
    patient_vector = patient_row[feature_cols].to_numpy(dtype=float)
    ranked = []
    for _, prototype in prototypes.iterrows():
        prototype_vector = prototype[feature_cols].to_numpy(dtype=float)
        normalized_diff = (patient_vector - prototype_vector) / scale_vector
        distance = float(np.sqrt(np.sum((normalized_diff * weights) ** 2)))
        ranked.append(
            {
                "prototype_id": prototype["prototype_id"],
                "therapy_track": prototype["therapy_track"],
                "distance": distance,
            }
        )
    ranked.sort(key=lambda item: (item["distance"], item["prototype_id"]))
    return ranked


profile_summaries = []
for _, profile in profiles.iterrows():
    weights = profile[weight_cols].to_numpy(dtype=float)
    correct = 0
    expected_distances = []

    for _, patient in validation.iterrows():
        rankings = rank_prototypes(patient, weights)
        if rankings[0]["prototype_id"] == patient["expected_best_prototype"]:
            correct += 1

        expected_distance = next(
            item["distance"]
            for item in rankings
            if item["prototype_id"] == patient["expected_best_prototype"]
        )
        expected_distances.append(expected_distance)

    profile_summaries.append(
        {
            "profile_id": profile["profile_id"],
            "validation_accuracy": correct / len(validation),
            "validation_mean_expected_distance": float(np.mean(expected_distances)),
            "weights": weights,
        }
    )

best_profile = sorted(
    profile_summaries,
    key=lambda item: (
        -item["validation_accuracy"],
        item["validation_mean_expected_distance"],
        item["profile_id"],
    ),
)[0]

rows = []
for _, patient in query.sort_values("patient_id").iterrows():
    rankings = rank_prototypes(patient, best_profile["weights"])[:3]
    for rank, item in enumerate(rankings, start=1):
        rows.append(
            {
                "patient_id": patient["patient_id"],
                "rank": rank,
                "prototype_id": item["prototype_id"],
                "therapy_track": item["therapy_track"],
                "distance": item["distance"],
                "selected_profile": best_profile["profile_id"],
                "validation_accuracy": best_profile["validation_accuracy"],
            }
        )

result = pd.DataFrame(rows)[
    [
        "patient_id",
        "rank",
        "prototype_id",
        "therapy_track",
        "distance",
        "selected_profile",
        "validation_accuracy",
    ]
]
result.to_csv(output_path, index=False, float_format="%.5f")
PY
