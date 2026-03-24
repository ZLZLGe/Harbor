#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import os
from pathlib import Path

INPUT_PATH = Path(os.environ.get("AUDIOBOOK_INPUT_JSON", "/root/audiobook_dialogue_segments.json"))
OUTPUT_PATH = Path(os.environ.get("VOICE_CAST_LEDGER_CSV", "/root/voice_cast_ledger.csv"))

FIELDNAMES = [
    "row_type",
    "book_id",
    "voice_cast_id",
    "chapter_id",
    "chapter_number",
    "segment_id",
    "start_sec",
    "end_sec",
    "duration_sec",
    "chapter_count",
    "segment_count",
    "total_dialogue_duration_sec",
    "first_chapter_number",
    "transcript_excerpt",
]


def flatten_dialogue_segments(payload):
    rows = []
    for chapter in sorted(payload["chapters"], key=lambda item: item["chapter_number"]):
        for segment in sorted(chapter["segments"], key=lambda item: item["start_sec"]):
            if segment["role_hint"] != "dialogue":
                continue
            rows.append(
                {
                    "book_id": payload["book_id"],
                    "chapter_id": chapter["chapter_id"],
                    "chapter_number": chapter["chapter_number"],
                    "segment_id": segment["segment_id"],
                    "start_sec": float(segment["start_sec"]),
                    "end_sec": float(segment["end_sec"]),
                    "duration_sec": float(segment["end_sec"]) - float(segment["start_sec"]),
                    "transcript_excerpt": segment["transcript_excerpt"],
                    "embedding": [float(value) for value in segment["embedding"]],
                }
            )
    return rows


def normalize(vector):
    norm = sum(value * value for value in vector) ** 0.5
    return [value / norm for value in vector]


def cosine_distance(left, right):
    return 1.0 - sum(a * b for a, b in zip(left, right))


def average_linkage_distance(left_members, right_members, normalized_vectors):
    distances = []
    for left_index in left_members:
        for right_index in right_members:
            distances.append(cosine_distance(normalized_vectors[left_index], normalized_vectors[right_index]))
    return sum(distances) / len(distances)


def choose_threshold(normalized_vectors):
    clusters = [[index] for index in range(len(normalized_vectors))]
    merge_distances = []
    while len(clusters) > 1:
        best_distance = None
        best_pair = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = average_linkage_distance(clusters[left_index], clusters[right_index], normalized_vectors)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_pair = (left_index, right_index)
        merge_distances.append(best_distance)
        left_index, right_index = best_pair
        clusters[left_index] = clusters[left_index] + clusters[right_index]
        del clusters[right_index]

    gap_index = 0
    best_ratio = None
    for index in range(len(merge_distances) - 1):
        current = max(merge_distances[index], 1e-12)
        following = merge_distances[index + 1]
        ratio = following / current
        if best_ratio is None or ratio > best_ratio:
            best_ratio = ratio
            gap_index = index
    return (merge_distances[gap_index] + merge_distances[gap_index + 1]) / 2.0


def cluster_segments(normalized_vectors, threshold):
    clusters = [[index] for index in range(len(normalized_vectors))]
    while True:
        best_distance = None
        best_pair = None
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = average_linkage_distance(clusters[left_index], clusters[right_index], normalized_vectors)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_pair = (left_index, right_index)
        if best_distance is None or best_distance > threshold:
            break
        left_index, right_index = best_pair
        clusters[left_index] = clusters[left_index] + clusters[right_index]
        del clusters[right_index]
    return sorted(clusters, key=lambda members: min(members))


def build_rows(payload, dialogue_segments, clusters):
    index_to_cast = {}
    summaries = []
    detail_rows = []

    for cast_index, members in enumerate(clusters):
        voice_cast_id = f"voice_cast_{cast_index:02d}"
        cluster_segments = [dialogue_segments[index] for index in members]
        cluster_segments.sort(key=lambda item: (item["chapter_number"], item["start_sec"], item["segment_id"]))
        for member_index in members:
            index_to_cast[member_index] = voice_cast_id

        first_segment = cluster_segments[0]
        summaries.append(
            {
                "row_type": "cast_summary",
                "book_id": payload["book_id"],
                "voice_cast_id": voice_cast_id,
                "chapter_id": "",
                "chapter_number": "",
                "segment_id": "",
                "start_sec": "",
                "end_sec": "",
                "duration_sec": "",
                "chapter_count": str(len({item["chapter_id"] for item in cluster_segments})),
                "segment_count": str(len(cluster_segments)),
                "total_dialogue_duration_sec": f"{sum(item['duration_sec'] for item in cluster_segments):.2f}",
                "first_chapter_number": str(first_segment["chapter_number"]),
                "transcript_excerpt": first_segment["transcript_excerpt"],
            }
        )

    for index, segment in enumerate(dialogue_segments):
        detail_rows.append(
            {
                "row_type": "segment_detail",
                "book_id": payload["book_id"],
                "voice_cast_id": index_to_cast[index],
                "chapter_id": segment["chapter_id"],
                "chapter_number": str(segment["chapter_number"]),
                "segment_id": segment["segment_id"],
                "start_sec": f"{segment['start_sec']:.2f}",
                "end_sec": f"{segment['end_sec']:.2f}",
                "duration_sec": f"{segment['duration_sec']:.2f}",
                "chapter_count": "",
                "segment_count": "",
                "total_dialogue_duration_sec": "",
                "first_chapter_number": "",
                "transcript_excerpt": segment["transcript_excerpt"],
            }
        )

    return summaries + detail_rows


payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
dialogue_segments = flatten_dialogue_segments(payload)
normalized_vectors = [normalize(segment["embedding"]) for segment in dialogue_segments]
threshold = choose_threshold(normalized_vectors)
clusters = cluster_segments(normalized_vectors, threshold)
rows = build_rows(payload, dialogue_segments, clusters)

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)
PY
