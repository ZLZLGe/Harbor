#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path

import numpy as np

INPUT_PATH = Path(os.environ.get("CALL_CENTER_INPUT_JSON", "/root/call_center_segments.json"))
OUTPUT_PATH = Path(os.environ.get("AGENT_VOICE_ROSTER_JSON", "/root/agent_voice_roster.json"))


def load_segments(payload):
    rows = []
    for call in sorted(payload["calls"], key=lambda item: item["call_id"]):
        for segment in sorted(call["segments"], key=lambda item: item["segment_index"]):
            rows.append(
                {
                    "call_id": call["call_id"],
                    "queue": call["queue"],
                    "segment_id": segment["segment_id"],
                    "segment_index": segment["segment_index"],
                    "embedding": np.array(segment["embedding"], dtype=float),
                }
            )
    return rows


def normalize_embeddings(rows):
    matrix = np.stack([row["embedding"] for row in rows], axis=0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / norms


def cosine_distances(matrix):
    similarity = matrix @ matrix.T
    return 1.0 - similarity


def average_linkage_distance(left_members, right_members, distances):
    return float(np.mean(distances[np.ix_(left_members, right_members)]))


def choose_threshold(distances):
    clusters = [[index] for index in range(len(distances))]
    merge_distances = []

    while len(clusters) > 1:
        best_distance = None
        best_pair = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = average_linkage_distance(clusters[left_index], clusters[right_index], distances)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_pair = (left_index, right_index)
        merge_distances.append(float(best_distance))
        left_index, right_index = best_pair
        clusters[left_index] = clusters[left_index] + clusters[right_index]
        del clusters[right_index]

    ratios = []
    for index in range(len(merge_distances) - 1):
        current = merge_distances[index]
        following = merge_distances[index + 1]
        ratios.append(following / max(current, 1e-12))
    gap_index = int(np.argmax(np.array(ratios, dtype=float)))
    return float((merge_distances[gap_index] + merge_distances[gap_index + 1]) / 2.0)


def build_components(distances, threshold):
    clusters = [[index] for index in range(len(distances))]
    while True:
        best_distance = None
        best_pair = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = average_linkage_distance(clusters[left_index], clusters[right_index], distances)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_pair = (left_index, right_index)
        if best_distance is None or best_distance > threshold:
            break
        left_index, right_index = best_pair
        clusters[left_index] = clusters[left_index] + clusters[right_index]
        del clusters[right_index]
    return clusters


def assign_cluster_ids(rows, components):
    ordered = sorted(components, key=lambda members: min(members))
    index_to_cluster = {}
    for cluster_number, members in enumerate(ordered):
        cluster_id = f"cluster_{cluster_number:02d}"
        for index in members:
            index_to_cluster[index] = cluster_id
    return index_to_cluster


def build_output(payload, rows, index_to_cluster, threshold):
    min_agent_calls = int(payload["speaker_type_rule"]["agent_min_distinct_calls"])
    assignments = []
    cluster_to_segment_ids = {}
    cluster_to_call_ids = {}

    for index, row in enumerate(rows):
        cluster_id = index_to_cluster[index]
        cluster_to_segment_ids.setdefault(cluster_id, []).append(row["segment_id"])
        cluster_to_call_ids.setdefault(cluster_id, []).append(row["call_id"])

    cluster_entries = []
    cluster_types = {}
    for cluster_id in sorted(cluster_to_segment_ids):
        call_ids = sorted(set(cluster_to_call_ids[cluster_id]))
        segment_ids = sorted(cluster_to_segment_ids[cluster_id])
        speaker_type = "agent" if len(call_ids) >= min_agent_calls else "caller"
        cluster_types[cluster_id] = speaker_type
        cluster_entries.append(
            {
                "cluster_id": cluster_id,
                "speaker_type": speaker_type,
                "distinct_call_count": len(call_ids),
                "call_ids": call_ids,
                "segment_count": len(segment_ids),
                "segment_ids": segment_ids,
            }
        )

    for index, row in enumerate(rows):
        cluster_id = index_to_cluster[index]
        assignments.append(
            {
                "call_id": row["call_id"],
                "segment_id": row["segment_id"],
                "cluster_id": cluster_id,
                "speaker_type": cluster_types[cluster_id],
            }
        )

    def roster_for(speaker_type):
        roster = []
        for cluster in cluster_entries:
            if cluster["speaker_type"] != speaker_type:
                continue
            roster.append(
                {
                    "cluster_id": cluster["cluster_id"],
                    "call_ids": cluster["call_ids"],
                    "segment_count": cluster["segment_count"],
                }
            )
        return roster

    return {
        "dataset_id": payload["dataset_id"],
        "distance_threshold": round(threshold, 8),
        "clusters": cluster_entries,
        "agent_roster": roster_for("agent"),
        "caller_roster": roster_for("caller"),
        "segment_assignments": assignments,
    }


payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
rows = load_segments(payload)
matrix = normalize_embeddings(rows)
distances = cosine_distances(matrix)
threshold = choose_threshold(distances)
components = build_components(distances, threshold)
index_to_cluster = assign_cluster_ids(rows, components)
output = build_output(payload, rows, index_to_cluster, threshold)
OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
PY
