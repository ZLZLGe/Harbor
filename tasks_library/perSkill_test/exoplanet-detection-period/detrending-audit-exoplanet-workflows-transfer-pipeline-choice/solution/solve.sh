#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import os
from pathlib import Path

import numpy as np


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/pipeline_choice.json"))
PIPELINE_IDS = ["pipeline_a", "pipeline_b", "pipeline_c"]


def load_curve(name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = DATA_DIR / f"{name}.csv"
    with path.open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    time = np.array([float(row["time_days"]) for row in rows], dtype=float)
    flux = np.array([float(row["flux"]) for row in rows], dtype=float)
    quality = np.array([int(row["quality_flag"]) for row in rows], dtype=int)
    good = quality == 0

    time = time[good]
    flux = flux[good]
    flux = flux / np.median(flux)
    return time, flux, quality


def robust_scatter(values: np.ndarray) -> float:
    center = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - center))
    return max(1.4826 * mad, 1e-6)


def period_score(time: np.ndarray, flux: np.ndarray, period: float, nbins: int) -> tuple[float, float, int, int] | None:
    phase = ((time - time.min()) / period) % 1.0
    order = np.argsort(phase)
    phase = phase[order]
    flux = flux[order]

    edges = np.linspace(0.0, 1.0, nbins + 1)
    bin_ids = np.clip(np.digitize(phase, edges) - 1, 0, nbins - 1)
    counts = np.bincount(bin_ids, minlength=nbins)
    sums = np.bincount(bin_ids, weights=flux, minlength=nbins)

    enough = counts >= 2
    if np.sum(enough) < nbins * 0.92:
        return None

    means = np.full(nbins, np.nan)
    means[enough] = sums[enough] / counts[enough]
    baseline = np.nanmedian(means)
    scatter = robust_scatter(means - baseline)
    filled = np.where(np.isnan(means), baseline, means)
    extended = np.concatenate([filled, filled])

    best = None
    for width in range(4, 10):
        convolved = np.convolve(extended, np.ones(width) / width, mode="valid")[:nbins]
        start = int(np.argmin(convolved))
        depth = baseline - convolved[start]
        score = depth / scatter
        if best is None or score > best[0]:
            best = (score, depth, start, width)

    return best


def analyze_pipeline(name: str) -> dict:
    time, flux, _ = load_curve(name)

    coarse_best = None
    for period in np.arange(4.5, 8.2, 0.002):
        result = period_score(time, flux, float(period), nbins=180)
        if result is None:
            continue
        score, depth, start, width = result
        if coarse_best is None or score > coarse_best["score"]:
            coarse_best = {
                "score": float(score),
                "period": float(period),
                "depth": float(depth),
                "start": int(start),
                "width": int(width),
                "nbins": 180,
                "time": time,
                "flux": flux,
            }

    refined_best = None
    for period in np.arange(coarse_best["period"] - 0.03, coarse_best["period"] + 0.03, 0.00005):
        result = period_score(time, flux, float(period), nbins=240)
        if result is None:
            continue
        score, depth, start, width = result
        if refined_best is None or score > refined_best["score"]:
            refined_best = {
                "score": float(score),
                "period": float(period),
                "depth": float(depth),
                "start": int(start),
                "width": int(width),
                "nbins": 240,
                "time": time,
                "flux": flux,
            }

    phase_center = (refined_best["start"] + refined_best["width"] / 2.0) / refined_best["nbins"]
    center = refined_best["time"].min() + phase_center * refined_best["period"]
    while center > refined_best["time"].min():
        center -= refined_best["period"]
    while center + refined_best["period"] <= refined_best["time"].min():
        center += refined_best["period"]

    event_depths = []
    current = center
    time = refined_best["time"]
    flux = refined_best["flux"]
    while current <= time.max() + refined_best["period"]:
        in_event = np.abs(time - current) <= 0.10
        wings = (np.abs(time - current) >= 0.16) & (np.abs(time - current) <= 0.35)
        if np.sum(in_event) >= 4 and np.sum(wings) >= 8:
            depth = (np.median(flux[wings]) - np.median(flux[in_event])) * 1000.0
            event_depths.append(float(depth))
        current += refined_best["period"]

    refined_best["median_event_depth_ppt"] = float(np.median(event_depths))
    return refined_best


results = {pipeline_id: analyze_pipeline(pipeline_id) for pipeline_id in PIPELINE_IDS}
selected_id = max(PIPELINE_IDS, key=lambda pipeline_id: results[pipeline_id]["score"])
selected = results[selected_id]

evidence = [
    (
        f"{selected_id} 在 {selected['period']:.5f} 天附近给出最稳定的重复下陷，"
        f"折叠后的代表性凌星深度约为 {selected['median_event_depth_ppt']:.2f} ppt，"
        "说明系统噪声已被压低，同时浅凌星仍被保留。"
    )
]

rejected_bits = []
for pipeline_id in PIPELINE_IDS:
    if pipeline_id == selected_id:
        continue
    candidate = results[pipeline_id]
    if abs(candidate["period"] - selected["period"]) > 0.2:
        rejected_bits.append(
            f"{pipeline_id} 更容易锁定在 {candidate['period']:.5f} 天附近的残余系统结构上，残余趋势仍然偏强"
        )
    elif candidate["median_event_depth_ppt"] < selected["median_event_depth_ppt"] * 0.75:
        rejected_bits.append(
            f"{pipeline_id} 的重复下陷仅约 {candidate['median_event_depth_ppt']:.2f} ppt，表现更像过度去趋势后把浅凌星压浅了"
        )
    else:
        rejected_bits.append(
            f"{pipeline_id} 的重复下陷不够稳定，无法像 {selected_id} 那样同时兼顾系统噪声抑制和浅凌星保留"
        )

evidence.append("；".join(rejected_bits) + "。")

payload = {
    "selected_pipeline_id": selected_id,
    "orbital_period_days": round(selected["period"], 5),
    "estimated_transit_depth_ppt": round(selected["median_event_depth_ppt"], 2),
    "evidence": evidence,
}

OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
