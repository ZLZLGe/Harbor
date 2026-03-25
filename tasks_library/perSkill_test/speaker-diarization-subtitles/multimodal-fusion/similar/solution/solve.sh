#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

SEGMENTS = Path("/root/data/segment_draft.json")
VISUAL = Path("/root/data/visual_observations.json")
AUDIO_MAP = Path("/root/data/audio_cluster_map.json")
META = Path("/root/data/session_meta.json")

OUT_RTTM = Path("/root/diarization.rttm")
OUT_ASS = Path("/root/subtitles.ass")
OUT_REPORT = Path("/root/report.json")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_observation(midpoint: float, observations: list[dict]) -> dict:
    return min(observations, key=lambda item: abs(float(item["timestamp"]) - midpoint))


def ass_time(value: float) -> str:
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = value - (hours * 3600) - (minutes * 60)
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


segments = load_json(SEGMENTS)
observations = load_json(VISUAL)
audio_map = load_json(AUDIO_MAP)
track_map = load_json(META)["track_speaker_map"]
audio_duration = float(load_json(META)["audio_duration_sec"])

resolved_segments = []
visual_overrides = 0
audio_fallbacks = 0

for segment in segments:
    midpoint = (float(segment["start"]) + float(segment["end"])) / 2.0
    observation = nearest_observation(midpoint, observations)
    use_visual = (
        abs(float(observation["timestamp"]) - midpoint) <= 0.75
        and len(observation["lip_tracks"]) == 1
    )
    if use_visual:
        speaker = track_map[observation["lip_tracks"][0]]
        evidence = "visual-lip"
    else:
        speaker = audio_map[segment["audio_label"]]
        evidence = "audio-default"
        audio_fallbacks += 1
    if evidence == "visual-lip" and speaker != audio_map[segment["audio_label"]]:
        visual_overrides += 1

    resolved_segments.append(
        {
            "segment_id": segment["segment_id"],
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "duration": float(segment["end"]) - float(segment["start"]),
            "speaker": speaker,
            "transcript": segment["transcript"],
        }
    )

with OUT_RTTM.open("w", encoding="utf-8") as handle:
    for item in resolved_segments:
        handle.write(
            "SPEAKER input 1 "
            f"{item['start']:.6f} {item['duration']:.6f} <NA> <NA> {item['speaker']} <NA> <NA>\n"
        )

ass_header = """[Script Info]
Title: Multi-Camera Diarization Repair
ScriptType: v4.00+
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

with OUT_ASS.open("w", encoding="utf-8") as handle:
    handle.write(ass_header)
    for item in resolved_segments:
        speaker_name = "SPEAKER_" + item["speaker"][-2:]
        handle.write(
            "Dialogue: 0,"
            f"{ass_time(item['start'])},{ass_time(item['end'])},Default,,0,0,0,,"
            f"{speaker_name}: {item['transcript']}\n"
        )

report = {
    "num_speakers_pred": len({item["speaker"] for item in resolved_segments}),
    "total_speech_time_sec": round(sum(item["duration"] for item in resolved_segments), 2),
    "audio_duration_sec": round(audio_duration, 2),
    "steps_completed": ["load_inputs", "align_visual_evidence", "write_outputs"],
    "commands_used": ["python3"],
    "libraries_used": ["json"],
    "tools_used": {
        "alignment": "midpoint_nearest_observation",
        "subtitle_format": "ass_writer",
    },
    "visual_overrides": visual_overrides,
    "audio_fallbacks": audio_fallbacks,
    "notes": "Used lip activity when exactly one active face was available; otherwise fell back to the audio cluster map.",
}
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
PY
