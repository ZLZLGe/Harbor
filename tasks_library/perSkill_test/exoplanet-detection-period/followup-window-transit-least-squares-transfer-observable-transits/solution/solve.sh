#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math

import numpy as np
import pandas as pd


LIGHTCURVE_PATH = "/root/data/followup_lightcurve.csv"
WINDOWS_PATH = "/root/data/visibility_windows.json"
OUTPUT_PATH = "/root/observable_transits.json"


def preprocess(frame: pd.DataFrame) -> pd.DataFrame:
    good = frame.loc[frame["quality"] == 0, ["time_bjd", "flux", "flux_err"]].copy()
    median_flux = float(good["flux"].median())
    mad = float(np.median(np.abs(good["flux"] - median_flux)))
    if mad > 0.0:
        keep = np.abs(good["flux"] - median_flux) <= 5.0 * 1.4826 * mad
        good = good.loc[keep].copy()
    trend = good["flux"].rolling(window=241, center=True, min_periods=1).median()
    good["flat_flux"] = good["flux"] / trend
    return good.reset_index(drop=True)


def search_best_period(time: np.ndarray, flux: np.ndarray, periods: np.ndarray, bins: int, width: int):
    kernel = np.ones(width) / width
    reference = float(time.min())
    best = None
    best_score = -np.inf

    for period in periods:
        phase = ((time - reference) / period) % 1.0
        indices = np.floor(phase * bins).astype(int)
        indices[indices == bins] = bins - 1

        counts = np.bincount(indices, minlength=bins)
        sums = np.bincount(indices, weights=flux, minlength=bins)
        means = np.divide(sums, counts, out=np.full(bins, np.inf), where=counts > 0)

        extended = np.concatenate([means, means[: width - 1]])
        window_means = np.convolve(extended, kernel, mode="valid")[:bins]
        start = int(np.argmin(window_means))
        in_bins = [(start + offset) % bins for offset in range(width)]
        mask = np.isin(indices, in_bins)

        in_flux = flux[mask]
        out_flux = flux[~mask]
        scatter = 1.4826 * np.median(np.abs(out_flux - np.median(out_flux)))
        score = (np.median(out_flux) - np.median(in_flux)) * math.sqrt(mask.sum()) / scatter

        if score > best_score:
            best_score = score
            best = {
                "period": float(period),
                "start": start,
                "bins": bins,
                "width": width,
            }

    return best


def refine_ephemeris(clean: pd.DataFrame):
    time = clean["time_bjd"].to_numpy()
    flux = clean["flat_flux"].to_numpy()

    best = search_best_period(time, flux, np.linspace(2.5, 12.0, 700), bins=180, width=7)
    best = search_best_period(
        time,
        flux,
        np.linspace(best["period"] * 0.97, best["period"] * 1.03, 1200),
        bins=240,
        width=8,
    )
    best = search_best_period(
        time,
        flux,
        np.linspace(best["period"] * 0.995, best["period"] * 1.005, 2200),
        bins=320,
        width=10,
    )

    period = best["period"]
    center = (best["start"] + best["width"] / 2.0) / best["bins"]
    reference = float(time.min())
    approximate_t0 = reference + center * period

    phase = ((time - reference) / period) % 1.0
    phase_distance = np.abs(((phase - center + 0.5) % 1.0) - 0.5)
    mask = phase_distance < (best["width"] / best["bins"]) / 2.0

    local_times = time[mask]
    local_flux = flux[mask]
    transit_ids = np.rint((local_times - approximate_t0) / period).astype(int)

    centers = []
    cycle_numbers = []
    for cycle in np.unique(transit_ids):
        cycle_mask = transit_ids == cycle
        samples_t = local_times[cycle_mask]
        samples_f = local_flux[cycle_mask]
        weights = 1.0 - samples_f + 1.0e-6
        centers.append(float(np.average(samples_t, weights=weights)))
        cycle_numbers.append(int(cycle))

    fit_period, fit_t0 = np.polyfit(cycle_numbers, centers, 1)
    while fit_t0 < time.min():
        fit_t0 += fit_period
    while fit_t0 - fit_period >= time.min():
        fit_t0 -= fit_period

    return float(fit_period), float(fit_t0)


frame = pd.read_csv(LIGHTCURVE_PATH)
clean = preprocess(frame)
period, t0 = refine_ephemeris(clean)

reported_period = round(period, 5)
reported_t0 = round(t0, 5)

with open(WINDOWS_PATH, encoding="utf-8") as fh:
    windows = json.load(fh)

window_start = min(window["start_bjd"] for window in windows)
window_end = max(window["end_bjd"] for window in windows)
start_cycle = max(0, math.ceil((window_start - reported_t0) / reported_period))
end_cycle = math.floor((window_end - reported_t0) / reported_period)

events = []
for cycle in range(start_cycle, end_cycle + 1):
    mid_transit = round(reported_t0 + cycle * reported_period, 5)
    for window in windows:
        if window["start_bjd"] <= mid_transit <= window["end_bjd"]:
            events.append(
                {
                    "window_id": window["window_id"],
                    "transit_number": cycle,
                    "mid_transit_bjd": mid_transit,
                }
            )
            break

payload = {
    "period_days": reported_period,
    "t0_bjd": reported_t0,
    "observable_transits": events,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
    fh.write("\n")
PY
