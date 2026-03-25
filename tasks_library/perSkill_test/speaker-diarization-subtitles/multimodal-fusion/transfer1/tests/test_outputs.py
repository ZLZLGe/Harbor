import csv
import json
from pathlib import Path

SEGMENTS = Path("/root/data/alignment_segments.csv")
EVENTS = Path("/root/data/camera_events.json")
CATALOG = Path("/root/data/speaker_catalog.json")
OUT = Path("/root/transfer1_alignment_manifest.json")


def nearest_event(midpoint: float, events: list[dict]) -> dict:
    return min(events, key=lambda item: abs(float(item["timestamp"]) - midpoint))


def expected() -> list[dict]:
    with SEGMENTS.open("r", encoding="utf-8", newline="") as handle:
        segments = list(csv.DictReader(handle))
    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    audio_defaults = catalog["audio_defaults"]
    track_display_names = catalog["track_display_names"]

    rows = []
    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        midpoint = (start + end) / 2.0
        event = nearest_event(midpoint, events)
        if abs(float(event["timestamp"]) - midpoint) <= 0.8 and len(event["lip_tracks"]) == 1:
            assigned_speaker = track_display_names[event["lip_tracks"][0]]
            evidence = "visual-lip"
        elif abs(float(event["timestamp"]) - midpoint) <= 0.8 and len(event["visible_tracks"]) == 1:
            assigned_speaker = track_display_names[event["visible_tracks"][0]]
            evidence = "single-visible"
        else:
            assigned_speaker = audio_defaults[segment["audio_cluster"]]
            evidence = "audio-default"

        visible_names = {track_display_names[track] for track in event["visible_tracks"]}
        rows.append(
            {
                "segment_id": segment["segment_id"],
                "start": round(start, 2),
                "end": round(end, 2),
                "assigned_speaker": assigned_speaker,
                "on_screen": assigned_speaker in visible_names,
                "evidence": evidence,
                "subtitle_text": segment["subtitle_text"],
            }
        )
    return rows


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    assert json.loads(OUT.read_text(encoding="utf-8")) == expected()


if __name__ == "__main__":
    main()
