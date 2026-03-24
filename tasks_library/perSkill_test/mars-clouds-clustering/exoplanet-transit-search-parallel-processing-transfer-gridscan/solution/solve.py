#!/usr/bin/env python3

import os
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


PERIOD_GRID = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
DURATION_GRID = [2, 3, 4, 5]
DEPTH_GRID = [6, 8, 10, 12, 14]
EPOCH_GRID = [0, 6, 12, 18]
FALSE_ALARM_DELTA_CHI2 = 20.0
ROOT_DIR = Path(os.environ.get("HARBOR_ROOT", "/root"))


def load_star_data():
    data_dir = ROOT_DIR / "data"
    light_curves = pd.read_csv(data_dir / "light_curves.csv")
    catalog = pd.read_csv(data_dir / "validation_catalog.csv")

    records = []
    for row in catalog.itertuples(index=False):
        subset = light_curves.loc[light_curves["star_id"] == row.star_id]
        time_days = subset["time_days"].to_numpy(float)
        flux = subset["flux"].to_numpy(float)
        flux_err = subset["flux_err"].to_numpy(float)
        flat_chi2 = float(np.sum(((flux - 1.0) / flux_err) ** 2))
        records.append(
            {
                "star_id": row.star_id,
                "is_transiting": int(row.is_transiting),
                "time_days": time_days,
                "flux": flux,
                "flux_err": flux_err,
                "flat_chi2": flat_chi2,
                "n_obs": len(time_days),
            }
        )
    return records


def evaluate_template(params, star_data):
    period_days, duration_hours, depth_ppt, epoch_hours = params
    duration_days = duration_hours / 24.0
    depth = depth_ppt / 1000.0

    positive_scores = []
    negative_flags = []

    for record in star_data:
        phase = np.mod(record["time_days"] - epoch_hours / 24.0, period_days)
        model_flux = np.ones(record["n_obs"], dtype=float)
        model_flux[phase < duration_days] -= depth

        template_chi2 = float(np.sum(((record["flux"] - model_flux) / record["flux_err"]) ** 2))
        delta_chi2 = max(record["flat_chi2"] - template_chi2, 0.0)
        detection_score = delta_chi2 / record["n_obs"]

        if record["is_transiting"] == 1:
            positive_scores.append(detection_score)
        else:
            negative_flags.append(1 if delta_chi2 >= FALSE_ALARM_DELTA_CHI2 else 0)

    mean_detection_score = float(np.mean(positive_scores))
    false_alarm_rate = float(np.mean(negative_flags))
    composite_score = mean_detection_score - 0.75 * false_alarm_rate

    return {
        "composite_score": composite_score,
        "mean_detection_score": mean_detection_score,
        "false_alarm_rate": false_alarm_rate,
        "period_days": round(period_days, 1),
        "duration_hours": duration_hours,
        "depth_ppt": depth_ppt,
        "epoch_hours": epoch_hours,
    }


def main():
    star_data = load_star_data()
    all_params = list(product(PERIOD_GRID, DURATION_GRID, DEPTH_GRID, EPOCH_GRID))
    worker_count = min(32, os.cpu_count() or 1, len(all_params))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(lambda params: evaluate_template(params, star_data), all_params))

    rankings = pd.DataFrame(results).sort_values(
        [
            "composite_score",
            "mean_detection_score",
            "false_alarm_rate",
            "period_days",
            "duration_hours",
            "depth_ppt",
            "epoch_hours",
        ],
        ascending=[False, False, True, True, True, True, True],
    ).head(20).reset_index(drop=True)

    rankings.insert(0, "rank", np.arange(1, len(rankings) + 1))
    rankings["composite_score"] = rankings["composite_score"].round(6)
    rankings["mean_detection_score"] = rankings["mean_detection_score"].round(6)
    rankings["false_alarm_rate"] = rankings["false_alarm_rate"].round(6)
    rankings["period_days"] = rankings["period_days"].round(1)

    output_path = ROOT_DIR / "transit_template_rankings.csv"
    rankings.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
