#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json

import pandas as pd

SOURCE_FILE = "/root/data/pv_array_ratio.csv"
OUTPUT_FILE = "/root/pv_drift_report.json"

df = pd.read_csv(SOURCE_FILE)

maintenance_filtered = df.loc[df["maintenance_flag"] == 0].copy().reset_index(drop=True)

spike_reference = maintenance_filtered["power_ratio"].rolling(
    window=21,
    center=True,
    min_periods=11,
).median()
spike_mask = (maintenance_filtered["power_ratio"] - spike_reference).abs() > 0.035

clean = maintenance_filtered.loc[~spike_mask].copy().reset_index(drop=True)
drift_baseline = clean["power_ratio"].rolling(
    window=121,
    center=True,
    min_periods=61,
).median()
drift_baseline = drift_baseline.bfill().ffill()

clean_ratio = clean["power_ratio"] / drift_baseline
clean_ratio = clean_ratio / clean_ratio.median()
clean["clean_ratio"] = clean_ratio
clean["timestamp"] = pd.to_datetime(clean["timestamp"])

preclean_dispersion_mad = (maintenance_filtered["power_ratio"] - maintenance_filtered["power_ratio"].median()).abs().median()
cleaned_dispersion_mad = (clean["clean_ratio"] - 1.0).abs().median()
cleaned_std = clean["clean_ratio"].std(ddof=0)
stability_improvement_ratio = preclean_dispersion_mad / cleaned_dispersion_mad

stable_mask = (clean["clean_ratio"] - 1.0).abs() <= 0.006
best_start = None
best_end = None
current_start = None

for idx, is_stable in enumerate(stable_mask.tolist()):
    if not is_stable:
        current_start = None
        continue

    if idx == 0:
        current_start = 0
    else:
        previous_time = clean.loc[idx - 1, "timestamp"]
        current_time = clean.loc[idx, "timestamp"]
        contiguous = stable_mask.iloc[idx - 1] and (current_time - previous_time).total_seconds() == 60
        if not contiguous:
            current_start = idx

    if best_start is None:
        best_start = current_start
        best_end = idx
        continue

    current_length = idx - current_start + 1
    best_length = best_end - best_start + 1
    if current_length > best_length:
        best_start = current_start
        best_end = idx

stable_interval = clean.iloc[best_start : best_end + 1]

report = {
    "source_file": SOURCE_FILE,
    "removed_points": {
        "maintenance": int((df["maintenance_flag"] != 0).sum()),
        "spikes": int(spike_mask.sum()),
        "total": int((df["maintenance_flag"] != 0).sum() + spike_mask.sum()),
    },
    "cleaned_points": int(len(clean)),
    "preclean_dispersion_mad": float(preclean_dispersion_mad),
    "cleaned_dispersion_mad": float(cleaned_dispersion_mad),
    "cleaned_std": float(cleaned_std),
    "stability_improvement_ratio": float(stability_improvement_ratio),
    "longest_stable_generation_interval": {
        "start_timestamp": stable_interval["timestamp"].iloc[0].isoformat(),
        "end_timestamp": stable_interval["timestamp"].iloc[-1].isoformat(),
        "duration_minutes": int(len(stable_interval)),
        "n_points": int(len(stable_interval)),
        "mean_clean_ratio": float(stable_interval["clean_ratio"].mean()),
        "max_abs_deviation": float((stable_interval["clean_ratio"] - 1.0).abs().max()),
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=True, indent=2)
    f.write("\n")
PY
