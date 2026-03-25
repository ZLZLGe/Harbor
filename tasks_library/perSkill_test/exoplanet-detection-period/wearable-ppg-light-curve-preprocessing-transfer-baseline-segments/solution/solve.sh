#!/bin/bash
set -euo pipefail

INPUT_PATH="${INPUT_PATH:-/root/data/wearable_ppg_session.csv}"
OUTPUT_PATH="${OUTPUT_PATH:-/root/ppg_clean_segments.csv}"
export INPUT_PATH OUTPUT_PATH

python3 <<'PY'
import os

import numpy as np
import pandas as pd

input_path = os.environ["INPUT_PATH"]
output_path = os.environ["OUTPUT_PATH"]

data = pd.read_csv(input_path).sort_values("timestamp").reset_index(drop=True)
clean = data.loc[data["quality_flag"] == 0].copy().reset_index(drop=True)

# 先用局部中位数找出明显高于邻域的饱和尖峰。
local_baseline = clean["ppg_signal"].rolling(window=13, center=True, min_periods=1).median()
residual = clean["ppg_signal"] - local_baseline
mad = float(np.median(np.abs(residual - float(np.median(residual)))))
scale = 1.4826 * mad
threshold = max(0.06, 6.0 * scale)
clean = clean.loc[residual.abs() <= threshold].copy().reset_index(drop=True)

clean["gap"] = clean["timestamp"].diff().fillna(0.0)
clean["segment_id"] = (clean["gap"] > 1.2).cumsum() + 1

segments = []
for _, group in clean.groupby("segment_id", sort=True):
    group = group.copy().reset_index(drop=True)
    if len(group) < 180:
        continue

    baseline = group["ppg_signal"].rolling(window=51, center=True, min_periods=1).median()
    normalized = group["ppg_signal"] / baseline - 1.0
    normalized = normalized - float(np.median(normalized))

    segments.append(
        pd.DataFrame(
            {
                "timestamp": group["timestamp"].round(5),
                "normalized_signal": normalized.round(6),
                "segment_id": len(segments) + 1,
            }
        )
    )

result = pd.concat(segments, ignore_index=True)
result = result.sort_values(["timestamp", "segment_id"]).reset_index(drop=True)
result.to_csv(output_path, index=False)
PY
