#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
import pandas as pd

INPUT_PATH = Path("/root/data/occultation_session.csv")
OUTPUT_PATH = Path("/root/occultation_windows.json")
GAP_THRESHOLD_SECONDS = 90
MIN_POINTS = 25


def rolling_median(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, center=True, min_periods=1).median()


df = pd.read_csv(INPUT_PATH).sort_values("time_jd").reset_index(drop=True)

# 先按质量标记过滤，再基于局部中位数识别明显宇宙线尖峰。
clean = df[df["frame_quality"] == 0].copy().reset_index(drop=True)
local_median = rolling_median(clean["rel_flux"], 11)
residual = clean["rel_flux"] - local_median
mad = float(np.median(np.abs(residual - np.median(residual))))
threshold = max(0.025, 6.0 * 1.4826 * mad)
clean = clean.loc[residual.abs() <= threshold].copy().reset_index(drop=True)

gap_days = GAP_THRESHOLD_SECONDS / 86400.0
clean["gap"] = clean["time_jd"].diff().fillna(0.0)
clean["window_id"] = (clean["gap"] > gap_days).cumsum() + 1

windows = []
for next_id, (_, group) in enumerate(clean.groupby("window_id"), start=1):
    group = group.copy().reset_index(drop=True)
    if len(group) < MIN_POINTS:
        continue

    trend = rolling_median(group["rel_flux"], 15)
    normalized = group["rel_flux"] / trend
    normalized = normalized / float(np.median(normalized))
    normalized = normalized.astype(float)

    times = group["time_jd"].round(8).tolist()
    normalized_flux = normalized.round(6).tolist()
    arr = np.asarray(normalized_flux, dtype=float)

    windows.append(
        {
            "window_id": next_id,
            "start_time": times[0],
            "end_time": times[-1],
            "n_points": int(len(group)),
            "times": times,
            "normalized_flux": normalized_flux,
            "mean_flux": round(float(arr.mean()), 6),
            "median_flux": round(float(np.median(arr)), 6),
            "std_flux": round(float(arr.std(ddof=0)), 6),
        }
    )

payload = {
    "source_file": str(INPUT_PATH),
    "gap_threshold_seconds": GAP_THRESHOLD_SECONDS,
    "windows": windows,
}

OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
PY
