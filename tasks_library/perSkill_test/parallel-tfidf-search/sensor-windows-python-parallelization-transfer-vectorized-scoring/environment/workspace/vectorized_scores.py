#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from sensor_scoring_sequential import (
    REPORT_FIELDS,
    ScoreBatchResult,
    WindowScore,
    build_summary,
    classify_severity,
    load_sensor_windows,
)


def _score_chunk(
    values: np.ndarray,
    window_ids: np.ndarray,
    device_ids: np.ndarray,
    start_ticks: np.ndarray,
    end_ticks: np.ndarray,
    manifest: dict,
) -> list[WindowScore]:
    rolling_width = int(manifest["rolling_width"])
    threshold_z = float(manifest["threshold_z"])
    volatility_floor = float(manifest["volatility_floor"])
    spike_top_n = int(manifest["spike_top_n"])

    means = values.mean(axis=1)
    volatility = values.std(axis=1)

    cumulative = np.pad(np.cumsum(values, axis=1, dtype=np.float64), ((0, 0), (1, 0)))
    rolling_sums = cumulative[:, rolling_width:] - cumulative[:, :-rolling_width]
    rolling_means = rolling_sums / rolling_width

    squared = values * values
    cumulative_sq = np.pad(np.cumsum(squared, axis=1, dtype=np.float64), ((0, 0), (1, 0)))
    rolling_sq_sums = cumulative_sq[:, rolling_width:] - cumulative_sq[:, :-rolling_width]
    rolling_variance = np.maximum(rolling_sq_sums / rolling_width - rolling_means * rolling_means, 0.0)
    rolling_std = np.sqrt(rolling_variance)

    aligned = values[:, rolling_width - 1 :]
    z_scores = np.abs(aligned - rolling_means) / np.maximum(rolling_std, volatility_floor)

    if spike_top_n < z_scores.shape[1]:
        top_scores = np.partition(z_scores, z_scores.shape[1] - spike_top_n, axis=1)[:, -spike_top_n:]
    else:
        top_scores = z_scores

    spike_score = top_scores.mean(axis=1)
    leading_mean = values[:, :rolling_width].mean(axis=1)
    trailing_mean = values[:, -rolling_width:].mean(axis=1)
    drift_score = np.abs(trailing_mean - leading_mean) / np.maximum(volatility, volatility_floor)
    breach_count = np.count_nonzero(z_scores >= threshold_z, axis=1)
    breach_fraction = breach_count / z_scores.shape[1]

    anomaly_score = (
        float(manifest["spike_weight"]) * spike_score
        + float(manifest["drift_weight"]) * drift_score
        + float(manifest["breach_weight"]) * breach_fraction
    )
    anomaly_score = np.round(anomaly_score, 6)

    rounded_means = np.round(means, 6)
    rounded_volatility = np.round(volatility, 6)
    rounded_spike = np.round(spike_score, 6)
    rounded_drift = np.round(drift_score, 6)

    scores: list[WindowScore] = []
    for index in range(values.shape[0]):
        score = float(anomaly_score[index])
        scores.append(
            WindowScore(
                window_id=int(window_ids[index]),
                device_id=str(device_ids[index]),
                start_tick=int(start_ticks[index]),
                end_tick=int(end_ticks[index]),
                mean_level=float(rounded_means[index]),
                volatility=float(rounded_volatility[index]),
                spike_score=float(rounded_spike[index]),
                drift_score=float(rounded_drift[index]),
                breach_count=int(breach_count[index]),
                anomaly_score=score,
                severity_band=classify_severity(score, manifest["severity_thresholds"]),
            )
        )
    return scores


def score_sensor_windows_vectorized(
    windows_path: str | Path = "/root/workspace/sensor_windows.npz",
    manifest_path: str | Path = "/root/workspace/window_manifest.json",
    chunk_size: int | None = None,
) -> ScoreBatchResult:
    start_time = time.perf_counter()
    measurements, window_ids, device_ids, start_ticks, end_ticks, manifest = load_sensor_windows(
        windows_path=windows_path,
        manifest_path=manifest_path,
    )

    if chunk_size is None or chunk_size <= 0:
        chunk_size = len(window_ids)

    scores: list[WindowScore] = []
    for start in range(0, len(window_ids), chunk_size):
        stop = min(start + chunk_size, len(window_ids))
        scores.extend(
            _score_chunk(
                measurements[start:stop],
                window_ids[start:stop],
                device_ids[start:stop],
                start_ticks[start:stop],
                end_ticks[start:stop],
                manifest,
            )
        )

    summary = build_summary(scores, manifest)
    elapsed_time = time.perf_counter() - start_time
    return ScoreBatchResult(
        scores=scores,
        summary=summary,
        elapsed_time=elapsed_time,
        window_count=len(scores),
    )


def write_window_score_report(
    windows_path: str | Path = "/root/workspace/sensor_windows.npz",
    manifest_path: str | Path = "/root/workspace/window_manifest.json",
    output_path: str | Path = "/root/workspace/window_scores_report.csv",
    chunk_size: int | None = None,
):
    batch_result = score_sensor_windows_vectorized(
        windows_path=windows_path,
        manifest_path=manifest_path,
        chunk_size=chunk_size,
    )
    output_file = Path(output_path)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for score in batch_result.scores:
            writer.writerow(asdict(score))
    return batch_result.summary


if __name__ == "__main__":
    write_window_score_report()
