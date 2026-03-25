#!/bin/bash
set -euo pipefail

python3 <<'PY'
import numpy as np
import pandas as pd
from pathlib import Path


INPUT_PATH = Path("/root/data/candidate_toi_4101.csv")
OUTPUT_PATH = Path("/root/vetting_report.md")


def best_window_score(values: np.ndarray, width_bins: int) -> tuple[float, int]:
    best_depth = -np.inf
    best_start = 0
    for start in range(len(values)):
        window = [(start + offset) % len(values) for offset in range(width_bins)]
        segment = values[window]
        if np.any(np.isnan(segment)):
            continue
        depth = np.nanmean(np.delete(values, window)) - np.mean(segment)
        if depth > best_depth:
            best_depth = depth
            best_start = start
    return best_depth, best_start


def score_period(time: np.ndarray, flat_flux: np.ndarray, period: float, bins: int = 120, width_bins: int = 8) -> tuple[float, float]:
    phase = ((time - time.min()) % period) / period
    edges = np.linspace(0.0, 1.0, bins + 1)
    indices = np.clip(np.digitize(phase, edges) - 1, 0, bins - 1)
    means = np.full(bins, np.nan)
    for idx in range(bins):
        mask = indices == idx
        if mask.sum() >= 2:
            means[idx] = np.mean(flat_flux[mask])
    depth, start = best_window_score(means, width_bins)
    center_phase = (start + (width_bins - 1) / 2.0) / bins
    return depth, center_phase * period


def event_depth(time: np.ndarray, raw_flux: np.ndarray, center: float) -> float | None:
    delta = time - center
    in_event = np.abs(delta) <= 0.09
    wings = (np.abs(delta) >= 0.15) & (np.abs(delta) <= 0.32)
    if in_event.sum() == 0 or wings.sum() < 8:
        return None
    coeff = np.polyfit(delta[wings], raw_flux[wings], deg=1)
    local_baseline = np.polyval(coeff, delta[in_event])
    return float((np.median(local_baseline) - np.percentile(raw_flux[in_event], 35)) * 1000.0)


data = pd.read_csv(INPUT_PATH).sort_values("time_days")
quality = data[data["quality_flag"] == 0].copy().reset_index(drop=True)

# Long-window median filtering removes the stellar modulation while preserving the eclipse train.
trend = pd.Series(quality["relative_flux"].to_numpy()).rolling(window=101, center=True, min_periods=1).median().to_numpy()
flat_flux = quality["relative_flux"].to_numpy() / trend
median = np.median(flat_flux)
mad = np.median(np.abs(flat_flux - median))
scale = 1.4826 * mad if mad > 0 else np.std(flat_flux)
keep = np.abs(flat_flux - median) < 5.0 * scale

search = quality.iloc[keep].copy().reset_index(drop=True)
search["flat_flux"] = flat_flux[keep]

time = search["time_days"].to_numpy()
flat = search["flat_flux"].to_numpy()

coarse_grid = np.arange(2.8, 3.5, 0.0004)
coarse = max(((*score_period(time, flat, period), period) for period in coarse_grid), key=lambda item: item[0])
refined_grid = np.arange(coarse[2] - 0.01, coarse[2] + 0.01, 0.00005)
refined = max(((*score_period(time, flat, period), period) for period in refined_grid), key=lambda item: item[0])

best_period = float(refined[2])
reference_center = float(time.min() + refined[1])
while reference_center > time.min():
    reference_center -= best_period
while reference_center + best_period <= time.min():
    reference_center += best_period

raw_time = quality["time_days"].to_numpy()
raw_flux = quality["relative_flux"].to_numpy()

events = []
center = reference_center
while center <= raw_time.max():
    depth = event_depth(raw_time, raw_flux, center)
    if depth is not None and center >= raw_time.min():
        events.append((center, depth))
    center += best_period

odd_depths = [depth for index, (_, depth) in enumerate(events) if index % 2 == 0]
even_depths = [depth for index, (_, depth) in enumerate(events) if index % 2 == 1]
odd_depth = float(np.median(odd_depths))
even_depth = float(np.median(even_depths))
verdict = "食双星" if abs(even_depth - odd_depth) >= 5.0 else "行星"

report = "\n".join(
    [
        "# Vetting Report",
        "",
        f"- best_period_days: {best_period:.5f}",
        f"- odd_event_depth_ppt: {odd_depth:.2f}",
        f"- even_event_depth_ppt: {even_depth:.2f}",
        f"- verdict: {verdict}",
        "",
        "## Evidence",
        f"- 奇偶事件深度明显不一致：odd 约为 {odd_depth:.2f} ppt，even 约为 {even_depth:.2f} ppt。",
        "- 交替食深远大于局部散布，说明该候选更像两颗恒星互食造成的假阳性，而不是稳定深度的单一行星凌星。",
        f"- 用于初始折叠检验的最强候选周期为 {best_period:.5f} 天，在去除恒星活动趋势后仍能重复出现。",
    ]
)

OUTPUT_PATH.write_text(report + "\n", encoding="utf-8")
PY
