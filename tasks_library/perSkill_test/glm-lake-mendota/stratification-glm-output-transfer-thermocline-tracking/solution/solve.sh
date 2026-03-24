#!/bin/bash
set -euo pipefail

python3 -u <<'PY'
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from netCDF4 import Dataset

SIM_ROOT = Path("/root")
NML_PATH = SIM_ROOT / "glm3.nml"
REF_PATH = SIM_ROOT / "manual_thermocline_reference.csv"
NC_PATH = SIM_ROOT / "output" / "output.nc"
REPORT_PATH = SIM_ROOT / "output" / "thermocline_tracking.csv"
WINDOW_START = pd.Timestamp("2013-04-29")
WINDOW_END = pd.Timestamp("2013-10-29")
GRADIENT_THRESHOLD = 1.0
MIN_DEPTH = 2.0
MAX_DEPTH = 20.0
MIN_COVERAGE = 0.75
TARGET_MAE = 3.5

BASE_NML = NML_PATH.read_text()


def parse_nml_value(name: str, text: str):
    match = re.search(rf"{name}\s*=\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(rf"{name}\s*=\s*([-+0-9.eE]+)", text)
    if match:
        return float(match.group(1))
    raise ValueError(f"Missing {name} in glm3.nml")


START_TIME = pd.Timestamp(parse_nml_value("start", BASE_NML))
LAKE_DEPTH = float(parse_nml_value("lake_depth", BASE_NML))


def write_nml(params):
    text = BASE_NML
    for key, value in params.items():
        text = re.sub(rf"({key}\s*=\s*)[-+0-9.eE]+", rf"\g<1>{value}", text)
    NML_PATH.write_text(text)


def run_glm():
    result = subprocess.run(["glm"], cwd=SIM_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "glm failed")


def read_reference():
    ref = pd.read_csv(REF_PATH, parse_dates=["date", "observation_time"])
    ref["manual_stratified"] = ref["manual_stratified"].astype(str).str.lower() == "true"
    return ref.sort_values("date").reset_index(drop=True)


def detect_daily_thermocline():
    nc = Dataset(NC_PATH, "r")
    time = nc.variables["time"][:]
    z = nc.variables["z"][:]
    temp = nc.variables["temp"][:]
    rows = []
    for t_idx in range(len(time)):
        timestamp = START_TIME + pd.Timedelta(hours=float(time[t_idx]))
        day = timestamp.floor("D")
        if day < WINDOW_START or day > WINDOW_END:
            continue

        layers = []
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for layer_idx in range(len(heights)):
            h_val = heights[layer_idx]
            t_val = temps[layer_idx]
            if np.ma.is_masked(h_val) or np.ma.is_masked(t_val):
                continue
            depth = LAKE_DEPTH - float(h_val)
            if 0 <= depth <= LAKE_DEPTH:
                layers.append((depth, float(t_val)))

        if len(layers) < 2:
            rows.append(
                {
                    "date": day,
                    "model_stratified": 0,
                    "model_thermocline_depth_m": np.nan,
                    "model_max_gradient_c_per_m": np.nan,
                }
            )
            continue

        layers.sort(key=lambda item: item[0])
        best = None
        for (depth_a, temp_a), (depth_b, temp_b) in zip(layers, layers[1:]):
            delta_depth = depth_b - depth_a
            if delta_depth <= 0:
                continue
            gradient = (temp_a - temp_b) / delta_depth
            midpoint = (depth_a + depth_b) / 2.0
            candidate = (gradient, midpoint)
            if best is None or candidate[0] > best[0] or (
                candidate[0] == best[0] and candidate[1] < best[1]
            ):
                best = candidate

        if best is None:
            max_gradient = np.nan
            stratified = 0
            thermocline_depth = np.nan
        else:
            max_gradient, midpoint = best
            stratified = int(
                max_gradient >= GRADIENT_THRESHOLD and MIN_DEPTH <= midpoint <= MAX_DEPTH
            )
            thermocline_depth = midpoint if stratified else np.nan

        rows.append(
            {
                "date": day,
                "model_stratified": stratified,
                "model_thermocline_depth_m": thermocline_depth,
                "model_max_gradient_c_per_m": max_gradient,
            }
        )

    nc.close()
    tracking = pd.DataFrame(rows).sort_values("date").drop_duplicates("date", keep="first")
    full_dates = pd.DataFrame({"date": pd.date_range(WINDOW_START, WINDOW_END, freq="D")})
    tracking = full_dates.merge(tracking, on="date", how="left")
    tracking["model_stratified"] = tracking["model_stratified"].fillna(0).astype(int)
    return tracking


def build_tracking_table():
    tracking = detect_daily_thermocline()
    reference = read_reference()
    reference["reference_available"] = 1
    reference["reference_stratified"] = reference["manual_stratified"].astype(int)
    reference["reference_thermocline_depth_m"] = reference["manual_thermocline_depth_m"]

    merged = tracking.merge(
        reference[
            [
                "date",
                "reference_available",
                "reference_stratified",
                "reference_thermocline_depth_m",
            ]
        ],
        on="date",
        how="left",
    )
    merged["reference_available"] = merged["reference_available"].fillna(0).astype(int)
    merged["reference_stratified"] = merged["reference_stratified"].fillna(0).astype(int)
    merged["depth_error_m"] = (
        merged["model_thermocline_depth_m"] - merged["reference_thermocline_depth_m"]
    )
    merged["abs_depth_error_m"] = merged["depth_error_m"].abs()

    numeric_cols = [
        "model_thermocline_depth_m",
        "model_max_gradient_c_per_m",
        "reference_thermocline_depth_m",
        "depth_error_m",
        "abs_depth_error_m",
    ]
    merged[numeric_cols] = merged[numeric_cols].round(4)
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    return merged[
        [
            "date",
            "model_stratified",
            "model_thermocline_depth_m",
            "model_max_gradient_c_per_m",
            "reference_available",
            "reference_stratified",
            "reference_thermocline_depth_m",
            "depth_error_m",
            "abs_depth_error_m",
        ]
    ]


def evaluate_tracking(tracking):
    ref_mask = (tracking["reference_available"] == 1) & (tracking["reference_stratified"] == 1)
    ref_count = int(ref_mask.sum())
    matched = tracking.loc[ref_mask & (tracking["model_stratified"] == 1)].copy()
    coverage = len(matched) / ref_count if ref_count else 0.0
    mae = float(matched["abs_depth_error_m"].mean()) if len(matched) else float("inf")
    score = mae + (1.0 - coverage) * 10.0
    return {
        "coverage": coverage,
        "mae": mae,
        "score": score,
        "matched_count": len(matched),
        "ref_count": ref_count,
    }


def main():
    candidates = [
        {"Kw": 0.30, "wind_factor": 1.00, "coef_mix_hyp": 0.50},
        {"Kw": 0.28, "wind_factor": 1.00, "coef_mix_hyp": 0.50},
        {"Kw": 0.32, "wind_factor": 1.00, "coef_mix_hyp": 0.50},
        {"Kw": 0.30, "wind_factor": 0.95, "coef_mix_hyp": 0.50},
        {"Kw": 0.30, "wind_factor": 1.05, "coef_mix_hyp": 0.50},
        {"Kw": 0.30, "wind_factor": 1.00, "coef_mix_hyp": 0.45},
        {"Kw": 0.30, "wind_factor": 1.00, "coef_mix_hyp": 0.55},
        {"Kw": 0.28, "wind_factor": 0.95, "coef_mix_hyp": 0.45},
        {"Kw": 0.32, "wind_factor": 1.05, "coef_mix_hyp": 0.55},
    ]

    best = None
    for idx, params in enumerate(candidates, start=1):
        write_nml(params)
        run_glm()
        tracking = build_tracking_table()
        metrics = evaluate_tracking(tracking)
        print(
            f"[{idx}/{len(candidates)}] "
            f"Kw={params['Kw']:.2f}, wind_factor={params['wind_factor']:.2f}, "
            f"coef_mix_hyp={params['coef_mix_hyp']:.2f} -> "
            f"coverage={metrics['coverage']:.4f}, mae={metrics['mae']:.4f}"
        )
        if best is None or metrics["score"] < best["metrics"]["score"]:
            best = {"params": params, "metrics": metrics, "tracking": tracking}
        if metrics["coverage"] >= MIN_COVERAGE and metrics["mae"] < TARGET_MAE:
            break

    if best is None:
        raise RuntimeError("No successful GLM run was produced.")

    write_nml(best["params"])
    run_glm()
    final_tracking = build_tracking_table()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_tracking.to_csv(REPORT_PATH, index=False)
    print(
        f"Best coverage={best['metrics']['coverage']:.4f}, "
        f"MAE={best['metrics']['mae']:.4f}, matched={best['metrics']['matched_count']}"
    )
    print(f"Wrote {len(final_tracking)} rows to {REPORT_PATH}")


if __name__ == "__main__":
    main()
PY
