#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path

import numpy as np


data_dir = Path(os.environ.get("DATA_DIR", "/root/data"))
output_path = Path(os.environ.get("OUTPUT_PATH", "/root/sector_ephemeris.json"))

DATA_FILES = [
    data_dir / "sector_18.csv",
    data_dir / "sector_19.csv",
]


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(values, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(padded, kernel, mode="valid")


def sigma_clip_positive(residuals: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    center = np.median(residuals)
    mad = np.median(np.abs(residuals - center))
    scale = 1.4826 * mad if mad > 0 else np.std(residuals)
    limit = center + sigma * scale
    return residuals < limit


def load_and_flatten(path: Path) -> tuple[np.ndarray, np.ndarray]:
    raw = np.genfromtxt(path, delimiter=",", names=True)
    good = raw["quality_flag"] == 0
    time = raw["time_bkjd"][good]
    flux = raw["flux"][good]

    order = np.argsort(time)
    time = time[order]
    flux = flux[order]

    coarse = moving_average(flux, 121)
    keep = sigma_clip_positive(flux - coarse)
    time = time[keep]
    flux = flux[keep]

    trend = moving_average(flux, 121)
    flat_flux = flux / trend
    return time, flat_flux


def best_box_for_period(time: np.ndarray, flux: np.ndarray, period: float, nbins: int) -> tuple[float, int, int] | None:
    phase = ((time - time.min()) / period) % 1.0
    order = np.argsort(phase)
    phase = phase[order]
    flux = flux[order]

    bins = np.linspace(0.0, 1.0, nbins + 1)
    bin_ids = np.minimum(np.searchsorted(bins, phase, side="right") - 1, nbins - 1)
    sums = np.bincount(bin_ids, weights=flux, minlength=nbins)
    counts = np.bincount(bin_ids, minlength=nbins)
    if np.any(counts < 2):
        return None

    means = sums / counts
    overall = float(np.mean(means))
    extended = np.concatenate([means, means])

    best_score = None
    best_start = 0
    best_width = 0
    for width in range(4, 11):
        averaged = np.convolve(extended, np.ones(width) / width, mode="valid")[:nbins]
        start = int(np.argmin(averaged))
        depth = overall - float(averaged[start])
        score = depth * np.sqrt(width)
        if best_score is None or score > best_score:
            best_score = score
            best_start = start
            best_width = width

    return best_score, best_start, best_width


def search_period(time: np.ndarray, flux: np.ndarray) -> tuple[float, int, int, int]:
    best = None
    for period in np.linspace(2.0, 6.5, 3500):
        result = best_box_for_period(time, flux, float(period), nbins=180)
        if result is None:
            continue
        score, start, width = result
        if best is None or score > best[0]:
            best = (score, float(period), 180, start, width)

    assert best is not None
    center = best[1]
    refined = None
    for period in np.linspace(center - 0.01, center + 0.01, 5000):
        result = best_box_for_period(time, flux, float(period), nbins=260)
        if result is None:
            continue
        score, start, width = result
        if refined is None or score > refined[0]:
            refined = (score, float(period), 260, start, width)

    assert refined is not None
    return refined[1], refined[2], refined[3], refined[4]


def estimate_epoch(time: np.ndarray, flux: np.ndarray, period: float, nbins: int, start: int, width: int) -> float:
    phase_center = (start + width / 2.0) / nbins
    first_candidate = time.min() + phase_center * period
    cycle_shift = np.ceil((time.min() - first_candidate) / period)
    epoch = first_candidate + cycle_shift * period
    return float(epoch)


all_time = []
all_flux = []
for file_path in DATA_FILES:
    sector_time, sector_flux = load_and_flatten(file_path)
    all_time.append(sector_time)
    all_flux.append(sector_flux)

time = np.concatenate(all_time)
flux = np.concatenate(all_flux)
order = np.argsort(time)
time = time[order]
flux = flux[order]

period, nbins, start, width = search_period(time, flux)
epoch = estimate_epoch(time, flux, period, nbins, start, width)

result = {
    "orbital_period_days": round(period, 5),
    "reference_mid_transit_time_bkjd": round(epoch, 5),
}

output_path.write_text(
    json.dumps(result, indent=2) + "\n",
    encoding="ascii",
)
PY
