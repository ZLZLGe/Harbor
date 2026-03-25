#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

import numpy as np
import pandas as pd
from transitleastsquares import transitleastsquares


DATA_DIR = Path("/root/data/survey_targets")
OUTPUT_PATH = Path("/root/candidate_ranking.csv")
THRESHOLD = 9.0


def preprocess(frame: pd.DataFrame) -> pd.DataFrame:
    good = frame.loc[frame["quality"] == 0, ["time_days", "flux", "flux_err"]].copy()
    flux = good["flux"].to_numpy()
    median_flux = np.median(flux)
    mad = np.median(np.abs(flux - median_flux))
    if mad > 0:
        keep = np.abs(flux - median_flux) <= 5 * 1.4826 * mad
        good = good.loc[keep].copy()
    trend = good["flux"].rolling(window=97, center=True, min_periods=1).median()
    good["flat_flux"] = good["flux"] / trend
    return good.reset_index(drop=True)


def run_tls(frame: pd.DataFrame) -> tuple[float, float]:
    tls = transitleastsquares(
        frame["time_days"].to_numpy(),
        frame["flat_flux"].to_numpy(),
        frame["flux_err"].to_numpy(),
    )
    results = tls.power(
        period_min=1.5,
        period_max=12.0,
        use_threads=1,
        show_progress_bar=False,
        verbose=False,
    )
    return float(results.period), float(results.SDE)


rows = []
for csv_path in sorted(DATA_DIR.glob("*.csv")):
    target_id = csv_path.stem
    frame = pd.read_csv(csv_path)
    cleaned = preprocess(frame)
    best_period, tls_sde = run_tls(cleaned)
    if tls_sde >= THRESHOLD:
        rows.append(
            {
                "target_id": target_id,
                "best_period_days": round(best_period, 5),
                "tls_sde": round(tls_sde, 3),
            }
        )

result = pd.DataFrame(rows, columns=["target_id", "best_period_days", "tls_sde"])
if not result.empty:
    result = result.sort_values(["tls_sde", "target_id"], ascending=[False, True], kind="mergesort")
result.to_csv(OUTPUT_PATH, index=False)
PY
