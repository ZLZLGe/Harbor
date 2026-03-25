from __future__ import annotations

import json
import csv
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist
from sklearn.cluster import AgglomerativeClustering, KMeans


def load_records(config: dict) -> list[dict]:
    path = Path(config["input_path"])
    fmt = config["input_format"]
    start_field = config["start_field"]
    end_field = config["end_field"]
    segment_id_field = config["segment_id_field"]
    time_unit = config.get("time_unit", "sec")

    if fmt == "json":
        payload = json.loads(path.read_text())
    elif fmt == "jsonl":
        payload = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    elif fmt in {"csv", "tsv"}:
        delimiter = "," if fmt == "csv" else "\t"
        with path.open(newline="", encoding="utf-8") as handle:
            payload = list(csv.DictReader(handle, delimiter=delimiter))
    else:
        raise ValueError(f"Unsupported input_format: {fmt}")

    records = []
    for raw in payload:
        record = dict(raw)
        if "embedding_key" in config:
            embedding = [float(value) for value in raw[config["embedding_key"]]]
        else:
            embedding = [float(raw[field]) for field in config["embedding_fields"]]

        start = float(raw[start_field])
        end = float(raw[end_field])
        if time_unit == "ms":
            start /= 1000.0
            end /= 1000.0

        record["segment_id"] = str(raw[segment_id_field])
        record["start_sec"] = round(start, 3)
        record["end_sec"] = round(end, 3)
        record["duration_sec"] = round(end - start, 3)
        record["embedding"] = embedding
        records.append(record)

    return sorted(records, key=lambda item: (item["start_sec"], item["end_sec"], item["segment_id"]))


def normalize_embeddings(records: list[dict]) -> np.ndarray:
    matrix = np.asarray([row["embedding"] for row in records], dtype=float)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-9, None)


def cluster_records(records: list[dict], config: dict) -> list[str]:
    normalized = normalize_embeddings(records)
    method = config["method"]

    if method == "hierarchical_auto":
        distances = pdist(normalized, metric="cosine")
        linkage_matrix = linkage(distances, method="average")
        labels = None
        for threshold in config["threshold_candidates"]:
            candidate = fcluster(linkage_matrix, t=float(threshold), criterion="distance")
            cluster_count = len(set(candidate))
            if config["min_clusters"] <= cluster_count <= config["max_clusters"]:
                labels = candidate
                break
        if labels is None:
            labels = fcluster(linkage_matrix, t=float(config["threshold_candidates"][-1]), criterion="distance")
    elif method == "kmeans_fixed":
        model = KMeans(n_clusters=int(config["n_clusters"]), random_state=0, n_init=10)
        labels = model.fit_predict(normalized)
    elif method == "agglomerative_fixed":
        model = AgglomerativeClustering(
            n_clusters=int(config["n_clusters"]),
            metric="cosine",
            linkage="average",
        )
        labels = model.fit_predict(normalized)
    else:
        raise ValueError(f"Unsupported clustering method: {method}")

    label_map = {}
    rendered = []
    next_index = 1
    for raw_label in labels:
        key = int(raw_label)
        if key not in label_map:
            label_map[key] = f"speaker_{next_index:02d}"
            next_index += 1
        rendered.append(label_map[key])
    return rendered


def merge_adjacent(records: list[dict], labels: list[str], gap_threshold: float) -> list[dict]:
    merged = []
    for record, label in zip(records, labels):
        item = {
            "segment_ids": [record["segment_id"]],
            "speaker_label": label,
            "start_sec": record["start_sec"],
            "end_sec": record["end_sec"],
            "duration_sec": record["duration_sec"],
        }
        if not merged:
            merged.append(item)
            continue

        previous = merged[-1]
        gap = round(item["start_sec"] - previous["end_sec"], 3)
        if label == previous["speaker_label"] and gap <= float(gap_threshold):
            previous["segment_ids"].extend(item["segment_ids"])
            previous["end_sec"] = item["end_sec"]
            previous["duration_sec"] = round(previous["end_sec"] - previous["start_sec"], 3)
        else:
            merged.append(item)
    return merged


def speaker_durations(labels: list[str], records: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for label, record in zip(labels, records):
        totals[label] = round(totals.get(label, 0.0) + record["duration_sec"], 2)
    return totals


def to_rttm_label(speaker_label: str) -> str:
    index = int(speaker_label.split("_")[1]) - 1
    return f"spk{index:02d}"
