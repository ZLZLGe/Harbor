#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


REPORT_FIELDS = [
    "window_id",
    "device_id",
    "start_tick",
    "end_tick",
    "mean_level",
    "volatility",
    "spike_score",
    "drift_score",
    "breach_count",
    "anomaly_score",
    "severity_band",
]

SEVERITY_ORDER = ("stable", "watch", "elevated", "critical")


@dataclass(frozen=True)
class WindowScore:
    window_id: int
    device_id: str
    start_tick: int
    end_tick: int
    mean_level: float
    volatility: float
    spike_score: float
    drift_score: float
    breach_count: int
    anomaly_score: float
    severity_band: str


@dataclass
class ScoreBatchResult:
    scores: list[WindowScore]
    summary: dict[str, Any]
    elapsed_time: float
    window_count: int


def load_sensor_windows(
    windows_path: str | Path = "/root/workspace/sensor_windows.npz",
    manifest_path: str | Path = "/root/workspace/window_manifest.json",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    data = np.load(Path(windows_path), allow_pickle=False)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return (
        data["measurements"].astype(np.float64, copy=False),
        data["window_ids"].astype(np.int64, copy=False),
        data["device_ids"].astype(str, copy=False),
        data["start_ticks"].astype(np.int64, copy=False),
        data["end_ticks"].astype(np.int64, copy=False),
        manifest,
    )


def classify_severity(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds["critical"]:
        return "critical"
    if score >= thresholds["elevated"]:
        return "elevated"
    if score >= thresholds["watch"]:
        return "watch"
    return "stable"


def build_summary(scores: list[WindowScore], manifest: dict[str, Any]) -> dict[str, Any]:
    severity_counts = {label: 0 for label in SEVERITY_ORDER}
    hotspot_map: dict[str, dict[str, Any]] = {}

    for score in scores:
        severity_counts[score.severity_band] += 1
        hotspot = hotspot_map.setdefault(
            score.device_id,
            {
                "device_id": score.device_id,
                "elevated_or_worse": 0,
                "max_score": 0.0,
            },
        )
        if score.severity_band in {"elevated", "critical"}:
            hotspot["elevated_or_worse"] += 1
        if score.anomaly_score > hotspot["max_score"]:
            hotspot["max_score"] = score.anomaly_score

    top_windows = [
        score.window_id
        for score in sorted(
            scores,
            key=lambda item: (-item.anomaly_score, -item.breach_count, item.window_id),
        )[: manifest["top_summary_count"]]
    ]

    hotspot_rows = sorted(
        (
            {
                "device_id": row["device_id"],
                "elevated_or_worse": row["elevated_or_worse"],
                "max_score": round(float(row["max_score"]), 6),
            }
            for row in hotspot_map.values()
        ),
        key=lambda item: (-item["elevated_or_worse"], -item["max_score"], item["device_id"]),
    )[: manifest["hotspot_count"]]

    mean_score = round(sum(score.anomaly_score for score in scores) / len(scores), 6)
    max_score = round(max(score.anomaly_score for score in scores), 6)
    breach_total = sum(score.breach_count for score in scores)

    return {
        "batch_id": manifest["batch_id"],
        "window_count": len(scores),
        "rolling_width": manifest["rolling_width"],
        "threshold_z": manifest["threshold_z"],
        "mean_anomaly_score": mean_score,
        "max_anomaly_score": max_score,
        "total_breach_count": breach_total,
        "severity_counts": severity_counts,
        "top_windows": top_windows,
        "device_hotspots": hotspot_rows,
    }


def score_one_window(
    values: np.ndarray,
    window_id: int,
    device_id: str,
    start_tick: int,
    end_tick: int,
    manifest: dict[str, Any],
) -> WindowScore:
    rolling_width = int(manifest["rolling_width"])
    threshold_z = float(manifest["threshold_z"])
    volatility_floor = float(manifest["volatility_floor"])
    spike_top_n = int(manifest["spike_top_n"])

    raw_mean = float(sum(float(sample) for sample in values) / len(values))
    variance = sum((float(sample) - raw_mean) ** 2 for sample in values) / len(values)
    volatility = math.sqrt(variance)

    rolling_scores: list[float] = []
    for end_index in range(rolling_width - 1, len(values)):
        segment = values[end_index - rolling_width + 1 : end_index + 1]
        segment_mean = float(sum(float(sample) for sample in segment) / rolling_width)
        segment_variance = sum((float(sample) - segment_mean) ** 2 for sample in segment) / rolling_width
        segment_std = math.sqrt(segment_variance)
        denominator = max(segment_std, volatility_floor)
        rolling_scores.append(abs(float(values[end_index]) - segment_mean) / denominator)

    leading_mean = float(sum(float(sample) for sample in values[:rolling_width]) / rolling_width)
    trailing_mean = float(sum(float(sample) for sample in values[-rolling_width:]) / rolling_width)
    top_scores = sorted(rolling_scores, reverse=True)[:spike_top_n]
    spike_score = sum(top_scores) / len(top_scores)
    drift_score = abs(trailing_mean - leading_mean) / max(volatility, volatility_floor)
    breach_count = int(sum(score >= threshold_z for score in rolling_scores))
    breach_fraction = breach_count / len(rolling_scores)
    anomaly_score = (
        float(manifest["spike_weight"]) * spike_score
        + float(manifest["drift_weight"]) * drift_score
        + float(manifest["breach_weight"]) * breach_fraction
    )
    anomaly_score = round(anomaly_score, 6)

    return WindowScore(
        window_id=int(window_id),
        device_id=str(device_id),
        start_tick=int(start_tick),
        end_tick=int(end_tick),
        mean_level=round(raw_mean, 6),
        volatility=round(volatility, 6),
        spike_score=round(spike_score, 6),
        drift_score=round(drift_score, 6),
        breach_count=breach_count,
        anomaly_score=anomaly_score,
        severity_band=classify_severity(anomaly_score, manifest["severity_thresholds"]),
    )


def score_sensor_windows_sequential(
    windows_path: str | Path = "/root/workspace/sensor_windows.npz",
    manifest_path: str | Path = "/root/workspace/window_manifest.json",
) -> ScoreBatchResult:
    start_time = time.perf_counter()
    measurements, window_ids, device_ids, start_ticks, end_ticks, manifest = load_sensor_windows(
        windows_path=windows_path,
        manifest_path=manifest_path,
    )

    scores = [
        score_one_window(
            values=measurements[index],
            window_id=int(window_ids[index]),
            device_id=str(device_ids[index]),
            start_tick=int(start_ticks[index]),
            end_tick=int(end_ticks[index]),
            manifest=manifest,
        )
        for index in range(len(window_ids))
    ]
    summary = build_summary(scores, manifest)
    elapsed_time = time.perf_counter() - start_time
    return ScoreBatchResult(
        scores=scores,
        summary=summary,
        elapsed_time=elapsed_time,
        window_count=len(scores),
    )


def write_window_score_report_sequential(
    windows_path: str | Path = "/root/workspace/sensor_windows.npz",
    manifest_path: str | Path = "/root/workspace/window_manifest.json",
    output_path: str | Path = "/root/workspace/window_scores_report.csv",
) -> dict[str, Any]:
    batch_result = score_sensor_windows_sequential(
        windows_path=windows_path,
        manifest_path=manifest_path,
    )
    output_file = Path(output_path)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for score in batch_result.scores:
            writer.writerow(asdict(score))
    return batch_result.summary


if __name__ == "__main__":
    write_window_score_report_sequential()
