#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import os
from pathlib import Path


segments_path = Path(os.environ.get("SPEECH_SEGMENTS_PATH", "/root/speech_segments.csv"))
windows_path = Path(os.environ.get("PODIUM_MOTION_WINDOWS_PATH", "/root/podium_motion_windows.json"))
affinity_path = Path(os.environ.get("CLUSTER_SLOT_AFFINITY_PATH", "/root/cluster_slot_affinity.json"))
layout_path = Path(os.environ.get("STAGE_LAYOUT_PATH", "/root/stage_layout.json"))
output_path = Path(os.environ.get("PODIUM_OUTPUT_PATH", "/root/podium_speaking_times.csv"))


def load_segments(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


segments = load_segments(segments_path)
windows = load_json(windows_path)["windows"]
affinity = load_json(affinity_path)
slots = sorted(load_json(layout_path)["slots"], key=lambda item: item["display_order"])
slot_order = [item["slot_id"] for item in slots]
slot_rank = {slot_id: index for index, slot_id in enumerate(slot_order)}


def best_affinity_slot(cluster_name: str) -> str:
    scores = affinity[cluster_name]
    return max(slot_order, key=lambda slot_id: (scores[slot_id], -slot_rank[slot_id]))


segment_rows = []
summary = {
    slot_id: {"total_speaking_sec": 0.0, "speaking_turns": 0}
    for slot_id in slot_order
}

for segment in segments:
    start_sec = float(segment["start_sec"])
    end_sec = float(segment["end_sec"])
    duration_sec = end_sec - start_sec

    lip_overlap = {slot_id: 0.0 for slot_id in slot_order}
    for window in windows:
        overlap_sec = overlap(start_sec, end_sec, float(window["start_sec"]), float(window["end_sec"]))
        if overlap_sec <= 0:
            continue
        for slot_id in window["lip_motion_slots"]:
            lip_overlap[slot_id] += overlap_sec

    ranked_visual = sorted(
        lip_overlap.items(),
        key=lambda item: (-item[1], slot_rank[item[0]]),
    )
    best_slot, best_overlap = ranked_visual[0]
    second_overlap = ranked_visual[1][1] if len(ranked_visual) > 1 else 0.0

    if best_overlap > second_overlap and (best_overlap / duration_sec) >= 0.5:
        assigned_slot = best_slot
        assignment_basis = "visual_lip_motion"
    else:
        assigned_slot = best_affinity_slot(segment["audio_cluster"])
        assignment_basis = "audio_cluster_fallback"

    segment_rows.append(
        {
            "row_type": "segment",
            "slot_id": assigned_slot,
            "segment_id": segment["segment_id"],
            "start_sec": f"{start_sec:.2f}",
            "end_sec": f"{end_sec:.2f}",
            "duration_sec": f"{duration_sec:.2f}",
            "assignment_basis": assignment_basis,
            "total_speaking_sec": "",
            "speaking_turns": "",
        }
    )
    summary[assigned_slot]["total_speaking_sec"] += duration_sec
    summary[assigned_slot]["speaking_turns"] += 1

rows = segment_rows[:]
for slot_id in slot_order:
    rows.append(
        {
            "row_type": "summary",
            "slot_id": slot_id,
            "segment_id": "",
            "start_sec": "",
            "end_sec": "",
            "duration_sec": "",
            "assignment_basis": "",
            "total_speaking_sec": f"{summary[slot_id]['total_speaking_sec']:.2f}",
            "speaking_turns": str(summary[slot_id]["speaking_turns"]),
        }
    )

fieldnames = [
    "row_type",
    "slot_id",
    "segment_id",
    "start_sec",
    "end_sec",
    "duration_sec",
    "assignment_basis",
    "total_speaking_sec",
    "speaking_turns",
]

with output_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
