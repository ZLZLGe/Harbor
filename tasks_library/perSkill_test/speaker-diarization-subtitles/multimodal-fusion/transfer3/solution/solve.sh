#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from collections import defaultdict
from pathlib import Path

SCENES = Path("/root/data/scene_boundaries.json")
UTTERANCES = Path("/root/data/utterance_log.json")
FRAMES = Path("/root/data/visual_frames.json")
DIRECTORY = Path("/root/data/speaker_directory.json")
OUT = Path("/root/transfer3_scene_presence_summary.json")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_frame(midpoint: float, frames: list[dict]) -> dict:
    return min(frames, key=lambda item: abs(float(item["timestamp"]) - midpoint))


scenes = load_json(SCENES)
utterances = load_json(UTTERANCES)
frames = load_json(FRAMES)
directory = load_json(DIRECTORY)
audio_defaults = directory["audio_defaults"]
track_display_names = directory["track_display_names"]

scene_entries = {scene["scene_id"]: [] for scene in scenes}

for utterance in utterances:
    start = float(utterance["start"])
    end = float(utterance["end"])
    duration = end - start
    midpoint = (start + end) / 2.0
    frame = nearest_frame(midpoint, frames)
    audio_speaker = audio_defaults[utterance["audio_label"]]
    visual_speaker = None
    if abs(float(frame["timestamp"]) - midpoint) <= 0.75 and len(frame["lip_tracks"]) == 1:
        visual_speaker = track_display_names[frame["lip_tracks"][0]]
    assigned_speaker = visual_speaker or audio_speaker
    visible_names = [track_display_names[track] for track in frame["visible_tracks"]]

    entry = {
        "utterance_id": utterance["utterance_id"],
        "duration": duration,
        "assigned_speaker": assigned_speaker,
        "visual_supported": visual_speaker is not None,
        "visible_names": visible_names,
    }

    for scene in scenes:
        if float(scene["start"]) <= midpoint <= float(scene["end"]):
            scene_entries[scene["scene_id"]].append(entry)
            break

results = []
for scene in scenes:
    entries = scene_entries[scene["scene_id"]]
    duration_by_speaker = defaultdict(float)
    total_speech = 0.0
    visual_supported = 0.0
    for entry in entries:
        duration_by_speaker[entry["assigned_speaker"]] += entry["duration"]
        total_speech += entry["duration"]
        if entry["visual_supported"]:
            visual_supported += entry["duration"]

    dominant_speaker = max(duration_by_speaker.items(), key=lambda item: item[1])[0]
    supporting_segments = [
        entry["utterance_id"]
        for entry in entries
        if entry["assigned_speaker"] == dominant_speaker
    ]
    offscreen_segments = [
        entry["utterance_id"]
        for entry in entries
        if entry["assigned_speaker"] == dominant_speaker
        and dominant_speaker not in entry["visible_names"]
    ]

    results.append(
        {
            "scene_id": scene["scene_id"],
            "dominant_speaker": dominant_speaker,
            "total_speech_sec": round(total_speech, 2),
            "visual_support_ratio": round(visual_supported / total_speech, 2),
            "supporting_segments": supporting_segments,
            "offscreen_segments": offscreen_segments,
        }
    )

OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
PY
