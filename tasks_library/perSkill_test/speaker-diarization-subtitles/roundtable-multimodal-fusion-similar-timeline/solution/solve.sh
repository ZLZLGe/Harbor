#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path


audio_path = Path(os.environ.get("AUDIO_CANDIDATES_PATH", "/root/audio_turn_candidates.json"))
visual_path = Path(os.environ.get("VISUAL_WINDOWS_PATH", "/root/visual_windows.json"))
affinity_path = Path(os.environ.get("CLUSTER_FACE_AFFINITY_PATH", "/root/cluster_face_affinity.json"))
roster_path = Path(os.environ.get("SPEAKER_ROSTER_PATH", "/root/speaker_roster.json"))
output_path = Path(os.environ.get("SPEAKER_TIMELINE_PATH", "/root/speaker_timeline.json"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


audio_candidates = load_json(audio_path)["candidates"]
visual_windows = load_json(visual_path)["windows"]
cluster_affinity = load_json(affinity_path)
speaker_ids = {
    item["speaker_id"]
    for item in load_json(roster_path)["speakers"]
}


def best_speaker(cluster_name: str) -> str:
    scores = cluster_affinity[cluster_name]
    speaker_id = max(scores, key=scores.get)
    if speaker_id not in speaker_ids:
        raise ValueError(f"Unknown speaker_id from affinity table: {speaker_id}")
    return speaker_id


def midpoint_window(start_sec: float, end_sec: float) -> dict:
    midpoint = (start_sec + end_sec) / 2.0
    for window in visual_windows:
        if window["start_sec"] <= midpoint < window["end_sec"]:
            return window
    if midpoint == visual_windows[-1]["end_sec"]:
        return visual_windows[-1]
    raise ValueError(f"No visual window covers midpoint {midpoint}")


def confidence_for(window: dict, speaker_id: str) -> str:
    if window.get("active_face_id") == speaker_id:
        return "high"
    if speaker_id in window["visible_face_ids"]:
        return "medium"
    return "low"


def make_segment(start_sec: float, end_sec: float, speaker_id: str) -> dict:
    window = midpoint_window(start_sec, end_sec)
    return {
        "speaker_id": speaker_id,
        "start_sec": round(start_sec, 2),
        "end_sec": round(end_sec, 2),
        "visible_face_count": len(window["visible_face_ids"]),
        "lip_motion_confirmed": window.get("active_face_id") == speaker_id,
        "visual_confidence": confidence_for(window, speaker_id),
    }


timeline = []
for candidate in audio_candidates:
    start_sec = candidate["start_sec"]
    end_sec = candidate["end_sec"]
    if candidate["split_by_visual"]:
        for window in visual_windows:
            overlap_start = max(start_sec, window["start_sec"])
            overlap_end = min(end_sec, window["end_sec"])
            if overlap_end <= overlap_start:
                continue
            speaker_id = window.get("active_face_id") or best_speaker(candidate["audio_cluster"])
            timeline.append(make_segment(overlap_start, overlap_end, speaker_id))
    else:
        speaker_id = best_speaker(candidate["audio_cluster"])
        timeline.append(make_segment(start_sec, end_sec, speaker_id))

timeline.sort(key=lambda item: item["start_sec"])
output_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
PY
