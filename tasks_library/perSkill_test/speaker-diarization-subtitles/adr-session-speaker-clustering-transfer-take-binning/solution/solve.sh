#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import math
import os
from pathlib import Path

INPUT_PATH = Path(os.environ.get("ADR_SESSION_INPUT_JSON", "/root/adr_session_takes.json"))
OUTPUT_PATH = Path(os.environ.get("ADR_TAKE_BINS_TSV", "/root/adr_take_bins.tsv"))

FIELDNAMES = [
    "session_id",
    "actor_bin_id",
    "take_id",
    "cue_id",
    "slate",
    "record_order",
    "start_tc",
    "end_tc",
    "duration_sec",
    "pickup_group",
    "guide_track_ref",
    "bin_take_index",
]


def normalize(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("embedding norm must be positive")
    return [value / norm for value in vector]


def cosine_distance(left, right):
    return 1.0 - sum(a * b for a, b in zip(left, right))


def average_linkage_distance(left_members, right_members, distances):
    values = []
    for left_index in left_members:
        for right_index in right_members:
            values.append(distances[left_index][right_index])
    return sum(values) / len(values)


def cluster_fixed_k(distances, target_cluster_count):
    clusters = [[index] for index in range(len(distances))]
    while len(clusters) > target_cluster_count:
        best_distance = None
        best_pair = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = average_linkage_distance(clusters[left_index], clusters[right_index], distances)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_pair = (left_index, right_index)
        left_index, right_index = best_pair
        clusters[left_index] = clusters[left_index] + clusters[right_index]
        del clusters[right_index]
    return clusters


payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
takes = sorted(payload["takes"], key=lambda item: item["record_order"])
normalized_embeddings = [normalize([float(value) for value in take["embedding"]]) for take in takes]
distances = [
    [cosine_distance(normalized_embeddings[left], normalized_embeddings[right]) for right in range(len(takes))]
    for left in range(len(takes))
]

clusters = cluster_fixed_k(distances, int(payload["actor_count"]))
clusters.sort(key=lambda members: min(takes[index]["record_order"] for index in members))

take_to_bin = {}
take_to_bin_index = {}
for bin_number, members in enumerate(clusters):
    actor_bin_id = payload["bin_id_rule"].format(index=bin_number)
    ordered_members = sorted(members, key=lambda index: takes[index]["record_order"])
    for local_index, take_index in enumerate(ordered_members, start=1):
        take_to_bin[takes[take_index]["take_id"]] = actor_bin_id
        take_to_bin_index[takes[take_index]["take_id"]] = str(local_index)

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
    writer.writeheader()
    for take in takes:
        writer.writerow(
            {
                "session_id": payload["session_id"],
                "actor_bin_id": take_to_bin[take["take_id"]],
                "take_id": take["take_id"],
                "cue_id": take["cue_id"],
                "slate": take["slate"],
                "record_order": str(take["record_order"]),
                "start_tc": take["start_tc"],
                "end_tc": take["end_tc"],
                "duration_sec": f"{float(take['duration_sec']):.2f}",
                "pickup_group": take["pickup_group"],
                "guide_track_ref": take["guide_track_ref"],
                "bin_take_index": take_to_bin_index[take["take_id"]],
            }
        )
PY
