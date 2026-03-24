#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


TIME_SCALE = 1.5
FREQ_SCALE = 20.0
DATA_DIR = Path("/root/data")
OUTPUT_PATH = Path("/root/seismic_event_clusters.csv")


def weighted_distance_matrix(points, time_weight):
    scaled = points.astype(float).copy()
    scaled[:, 0] /= TIME_SCALE
    scaled[:, 1] /= FREQ_SCALE
    diff = scaled[:, np.newaxis, :] - scaled[np.newaxis, :, :]
    diff[:, :, 0] *= time_weight
    diff[:, :, 1] *= 2.0 - time_weight
    return np.sqrt((diff**2).sum(axis=2))


def dbscan_precomputed(dist_matrix, epsilon, min_samples):
    point_count = len(dist_matrix)
    labels = np.full(point_count, -99, dtype=int)
    neighbors = [np.where(dist_matrix[idx] <= epsilon)[0] for idx in range(point_count)]
    is_core = [len(items) >= min_samples for items in neighbors]
    cluster_id = 0

    for idx in range(point_count):
        if labels[idx] != -99:
            continue
        if not is_core[idx]:
            labels[idx] = -1
            continue

        labels[idx] = cluster_id
        seeds = [candidate for candidate in neighbors[idx] if candidate != idx]
        seen = set(seeds)
        cursor = 0

        while cursor < len(seeds):
            neighbor_idx = seeds[cursor]
            if labels[neighbor_idx] == -1:
                labels[neighbor_idx] = cluster_id
            if labels[neighbor_idx] != -99:
                cursor += 1
                continue

            labels[neighbor_idx] = cluster_id
            if is_core[neighbor_idx]:
                for candidate in neighbors[neighbor_idx]:
                    if candidate not in seen:
                        seeds.append(candidate)
                        seen.add(candidate)
            cursor += 1

        cluster_id += 1

    labels[labels == -99] = -1
    return labels


def greedy_match(centroids, references, max_distance=0.90):
    if len(centroids) == 0 or len(references) == 0:
        return 0, len(centroids), len(references), []

    centroids = centroids.astype(float).copy()
    references = references.astype(float).copy()
    centroids[:, 0] /= TIME_SCALE
    centroids[:, 1] /= FREQ_SCALE
    references[:, 0] /= TIME_SCALE
    references[:, 1] /= FREQ_SCALE

    distances = np.sqrt(((centroids[:, np.newaxis, :] - references[np.newaxis, :, :]) ** 2).sum(axis=2))
    matches = []

    while True:
        row_idx, col_idx = np.unravel_index(np.argmin(distances), distances.shape)
        best_distance = distances[row_idx, col_idx]
        if not np.isfinite(best_distance) or best_distance > max_distance:
            break
        matches.append((row_idx, col_idx, float(best_distance)))
        distances[row_idx, :] = np.inf
        distances[:, col_idx] = np.inf

    true_positive = len(matches)
    false_positive = len(centroids) - true_positive
    false_negative = len(references) - true_positive
    return true_positive, false_positive, false_negative, matches


def evaluate_config(calibration_peaks, calibration_refs, config):
    min_samples, epsilon, time_weight = config
    f1_scores = []
    centroid_errors = []

    for station_id in calibration_refs["station_id"].drop_duplicates():
        peaks = calibration_peaks.loc[
            calibration_peaks["station_id"] == station_id, ["time_sec", "frequency_hz"]
        ].to_numpy(dtype=float)
        references = calibration_refs.loc[
            calibration_refs["station_id"] == station_id, ["event_time_sec", "event_frequency_hz"]
        ].to_numpy(dtype=float)

        if len(peaks) == 0:
            f1_scores.append(0.0)
            continue

        labels = dbscan_precomputed(weighted_distance_matrix(peaks, time_weight), epsilon, min_samples)
        cluster_ids = [cluster_id for cluster_id in sorted(set(labels)) if cluster_id != -1]
        if not cluster_ids:
            f1_scores.append(0.0)
            continue

        centroids = np.array([peaks[labels == cluster_id].mean(axis=0) for cluster_id in cluster_ids])
        tp, fp, fn, matches = greedy_match(centroids, references)
        if tp == 0:
            f1_scores.append(0.0)
            continue

        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1_scores.append(2.0 * precision * recall / (precision + recall))
        centroid_errors.append(float(np.mean([match[2] for match in matches])))

    mean_f1 = float(np.mean(f1_scores))
    mean_error = float(np.mean(centroid_errors)) if centroid_errors else float("inf")
    return mean_f1, mean_error


def choose_best_config(calibration_peaks, calibration_refs):
    best_config = None
    best_rank = None

    for config in product([3, 4], [0.70, 0.85, 1.00, 1.15], [0.8, 1.0, 1.2, 1.4, 1.6]):
        mean_f1, mean_error = evaluate_config(calibration_peaks, calibration_refs, config)
        min_samples, epsilon, time_weight = config
        rank_key = (-mean_f1, mean_error, epsilon, min_samples, time_weight)
        if best_rank is None or rank_key < best_rank:
            best_rank = rank_key
            best_config = config

    return best_config


def summarize_clusters(survey_peaks, config):
    min_samples, epsilon, time_weight = config
    rows = []

    for station_id in sorted(survey_peaks["station_id"].unique()):
        station_peaks = survey_peaks.loc[survey_peaks["station_id"] == station_id].copy()
        points = station_peaks[["time_sec", "frequency_hz"]].to_numpy(dtype=float)
        labels = dbscan_precomputed(weighted_distance_matrix(points, time_weight), epsilon, min_samples)
        station_peaks["cluster_id"] = labels

        clusters = []
        for cluster_id in sorted(set(labels)):
            if cluster_id == -1:
                continue
            cluster = station_peaks.loc[station_peaks["cluster_id"] == cluster_id]
            clusters.append(
                {
                    "peak_count": int(len(cluster)),
                    "start_time_sec": float(cluster["time_sec"].min()),
                    "end_time_sec": float(cluster["time_sec"].max()),
                    "center_time_sec": float(cluster["time_sec"].mean()),
                    "min_frequency_hz": float(cluster["frequency_hz"].min()),
                    "max_frequency_hz": float(cluster["frequency_hz"].max()),
                    "center_frequency_hz": float(cluster["frequency_hz"].mean()),
                    "mean_amplitude_db": float(cluster["amplitude_db"].mean()),
                }
            )

        clusters.sort(key=lambda item: (item["center_time_sec"], item["center_frequency_hz"]))
        for index, cluster in enumerate(clusters, start=1):
            rows.append(
                {
                    "station_id": station_id,
                    "event_id": f"{station_id}_E{index:02d}",
                    **cluster,
                    "selected_time_weight": round(time_weight, 1),
                    "selected_epsilon": round(epsilon, 2),
                    "selected_min_samples": int(min_samples),
                }
            )

    result = pd.DataFrame(rows)
    for column in [
        "start_time_sec",
        "end_time_sec",
        "center_time_sec",
        "min_frequency_hz",
        "max_frequency_hz",
        "center_frequency_hz",
        "mean_amplitude_db",
    ]:
        result[column] = result[column].round(3)
    return result[
        [
            "station_id",
            "event_id",
            "peak_count",
            "start_time_sec",
            "end_time_sec",
            "center_time_sec",
            "min_frequency_hz",
            "max_frequency_hz",
            "center_frequency_hz",
            "mean_amplitude_db",
            "selected_time_weight",
            "selected_epsilon",
            "selected_min_samples",
        ]
    ]


def main():
    calibration_peaks = pd.read_csv(DATA_DIR / "calibration_peaks.csv")
    calibration_refs = pd.read_csv(DATA_DIR / "calibration_reference_events.csv")
    survey_peaks = pd.read_csv(DATA_DIR / "survey_peaks.csv")

    best_config = choose_best_config(calibration_peaks, calibration_refs)
    result = summarize_clusters(survey_peaks, best_config)
    result.to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
PY
