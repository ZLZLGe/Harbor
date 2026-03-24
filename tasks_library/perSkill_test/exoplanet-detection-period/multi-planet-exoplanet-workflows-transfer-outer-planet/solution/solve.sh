#!/bin/bash
set -euo pipefail

python3 <<'PY'
import numpy as np
import pandas as pd

DATA_PATH = "/root/data/two_planet_tess_lc.txt"
OUTPUT_PATH = "/root/outer_planet_period.txt"


def flatten_flux(flux):
    trend = pd.Series(flux).rolling(window=721, center=True, min_periods=1).median().to_numpy()
    flat = flux / trend
    return flat / np.median(flat)


def search_transit_period(time, flux, period_min, period_max, n_periods, durations, nbins):
    periods = np.linspace(period_min, period_max, n_periods)
    scatter = np.std(flux)
    best = None

    for period in periods:
        phase = ((time - time.min()) % period) / period
        bins = np.floor(phase * nbins).astype(int)
        bins = np.clip(bins, 0, nbins - 1)

        bin_sum = np.bincount(bins, weights=flux, minlength=nbins).astype(float)
        bin_count = np.bincount(bins, minlength=nbins).astype(float)

        ext_sum = np.concatenate([bin_sum, bin_sum])
        ext_count = np.concatenate([bin_count, bin_count])
        prefix_sum = np.concatenate([[0.0], np.cumsum(ext_sum)])
        prefix_count = np.concatenate([[0.0], np.cumsum(ext_count)])

        for duration in durations:
            width = max(1, int(round(duration / period * nbins)))
            if width >= nbins // 2:
                continue

            window_sum = (prefix_sum[width:] - prefix_sum[:-width])[:nbins]
            window_count = (prefix_count[width:] - prefix_count[:-width])[:nbins]
            ok = window_count > max(20, width * 5)
            if not np.any(ok):
                continue

            window_mean = np.divide(window_sum, window_count, out=np.full(nbins, np.inf), where=ok)
            start = int(np.argmin(window_mean))
            if not np.isfinite(window_mean[start]):
                continue

            depth = 1.0 - window_mean[start]
            score = depth * np.sqrt(window_count[start]) / scatter
            center_bin = (start + width / 2) / nbins
            epoch = time.min() + center_bin * period
            candidate = (score, period, epoch, duration)

            if best is None or candidate[0] > best[0]:
                best = candidate

    return best


raw = np.loadtxt(DATA_PATH)
time = raw[:, 0]
flux = raw[:, 1]
flag = raw[:, 2]

good = flag == 0
time = time[good]
flux = flux[good]

median_flux = np.median(flux)
mad = np.median(np.abs(flux - median_flux))
sigma = 1.4826 * mad
keep = np.abs(flux - median_flux) < 5 * sigma
time = time[keep]
flux = flux[keep]

flat_flux = flatten_flux(flux)

inner = search_transit_period(
    time,
    flat_flux,
    period_min=1.0,
    period_max=6.0,
    n_periods=1800,
    durations=[0.08, 0.12, 0.16, 0.20, 0.24],
    nbins=240,
)

_, inner_period, inner_epoch, inner_duration = inner
inner_phase = ((time - inner_epoch + 0.5 * inner_period) % inner_period) - 0.5 * inner_period
outer_mask = np.abs(inner_phase) > 0.75 * inner_duration

outer_coarse = search_transit_period(
    time[outer_mask],
    flat_flux[outer_mask],
    period_min=4.5,
    period_max=15.0,
    n_periods=2200,
    durations=[0.12, 0.16, 0.20, 0.24, 0.28, 0.32],
    nbins=280,
)

_, coarse_period, _, coarse_duration = outer_coarse
outer_refined = search_transit_period(
    time[outer_mask],
    flat_flux[outer_mask],
    period_min=coarse_period * 0.95,
    period_max=coarse_period * 1.05,
    n_periods=2400,
    durations=[max(0.08, coarse_duration - 0.04), coarse_duration, min(0.40, coarse_duration + 0.04)],
    nbins=320,
)

outer_period = outer_refined[1]

with open(OUTPUT_PATH, "w") as fh:
    fh.write(f"{outer_period:.5f}\n")
PY
