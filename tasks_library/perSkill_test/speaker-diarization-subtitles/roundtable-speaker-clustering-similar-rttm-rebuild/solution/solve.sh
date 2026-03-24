#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

INPUT_PATH = Path("/root/panel_segments.json")
OUTPUT_PATH = Path("/root/panel_diarization.rttm")


def load_segments(path: Path):
    data = json.loads(path.read_text())
    segments = sorted(data["segments"], key=lambda item: (item["start"], item["end"]))
    return data, segments


def normalize_rows(array: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    return array / np.clip(norms, 1e-12, None)


def choose_labels(embeddings: np.ndarray, min_speakers: int, max_speakers: int) -> np.ndarray:
    best_score = None
    best_labels = None
    upper = min(max_speakers, len(embeddings) - 1)
    for k in range(min_speakers, upper + 1):
        model = AgglomerativeClustering(
            n_clusters=k,
            metric="cosine",
            linkage="average",
        )
        labels = model.fit_predict(embeddings)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(embeddings, labels, metric="cosine")
        if best_score is None or score > best_score:
            best_score = score
            best_labels = labels
    if best_labels is None:
        raise RuntimeError("failed to choose clustering labels")
    return best_labels


def assign_speakers(segments, labels):
    cluster_to_name = {}
    labeled = []
    next_index = 0
    for segment, label in zip(segments, labels):
        if label not in cluster_to_name:
            cluster_to_name[label] = f"spk{next_index:02d}"
            next_index += 1
        labeled.append(
            {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "speaker": cluster_to_name[label],
            }
        )
    return labeled


def merge_segments(segments, max_gap: float):
    merged = [segments[0].copy()]
    for segment in segments[1:]:
        current = merged[-1]
        gap = segment["start"] - current["end"]
        if segment["speaker"] == current["speaker"] and gap <= max_gap:
            current["end"] = segment["end"]
        else:
            merged.append(segment.copy())
    return merged


def write_rttm(path: Path, session_id: str, segments):
    with path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            start = segment["start"]
            duration = segment["end"] - segment["start"]
            handle.write(
                f"SPEAKER {session_id} 1 {start:.6f} {duration:.6f} <NA> <NA> {segment['speaker']} <NA> <NA>\n"
            )


metadata, segments = load_segments(INPUT_PATH)
embeddings = normalize_rows(np.array([segment["embedding"] for segment in segments], dtype=float))
min_speakers, max_speakers = metadata["speaker_count_range"]
labels = choose_labels(embeddings, min_speakers=min_speakers, max_speakers=max_speakers)
labeled_segments = assign_speakers(segments, labels)
merged_segments = merge_segments(labeled_segments, max_gap=float(metadata["merge_gap_sec"]))
write_rttm(OUTPUT_PATH, session_id=metadata["session_id"], segments=merged_segments)
PY
