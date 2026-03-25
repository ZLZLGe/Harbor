#!/bin/bash
set -euo pipefail

python3 <<'PY'
import pandas as pd

INPUT_PATH = "/root/data/tess_s028_quicklook.csv"
OUTPUT_PATH = "/root/transit_ready_lightcurve.csv"

data = pd.read_csv(INPUT_PATH)
data = data.loc[data["quality"] == 0].copy()
data = data.sort_values("time").reset_index(drop=True)

# Estimate the slow baseline first, then clip only extreme residual excursions.
baseline = data["sap_flux"].rolling(window=97, center=True, min_periods=1).median()
residual = data["sap_flux"] / baseline
median = residual.median()
mad = (residual - median).abs().median()
scale = 1.4826 * mad
keep = (residual - median).abs() < 8 * scale

clean = data.loc[keep, ["time", "sap_flux", "flux_err"]].copy()
clean = clean.sort_values("time").reset_index(drop=True)

trend = clean["sap_flux"].rolling(window=97, center=True, min_periods=1).median()
clean["flat_flux"] = clean["sap_flux"] / trend

result = clean[["time", "flat_flux", "flux_err"]]
result.to_csv(OUTPUT_PATH, index=False)
PY
