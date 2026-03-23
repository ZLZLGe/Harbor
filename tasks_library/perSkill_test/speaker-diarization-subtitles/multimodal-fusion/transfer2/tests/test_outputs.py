import csv
import json
from pathlib import Path

TURNS = Path("/root/data/draft_turns.json")
CHECKS = Path("/root/data/visual_checks.csv")
LABELS = Path("/root/data/label_defaults.json")
OUT = Path("/root/transfer2_review_queue.csv")


def parse_pipe_list(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    return [item for item in raw.split("|") if item]


def nearest_check(midpoint: float, checks: list[dict]) -> dict:
    return min(checks, key=lambda item: abs(float(item["timestamp"]) - midpoint))


def expected_rows() -> list[dict]:
    turns = json.loads(TURNS.read_text(encoding="utf-8"))
    with CHECKS.open("r", encoding="utf-8", newline="") as handle:
        checks = list(csv.DictReader(handle))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    audio_defaults = labels["audio_defaults"]
    track_display_names = labels["track_display_names"]

    rows = []
    for turn in turns:
        start = float(turn["start"])
        end = float(turn["end"])
        midpoint = (start + end) / 2.0
        check = nearest_check(midpoint, checks)
        visible_tracks = parse_pipe_list(check["visible_tracks"])
        lip_tracks = parse_pipe_list(check["lip_tracks"])
        audio_speaker = audio_defaults[turn["audio_label"]]

        review_reason = None
        recommended_action = None
        suggested_speaker = ""

        if abs(float(check["timestamp"]) - midpoint) <= 0.7 and len(lip_tracks) == 1:
            visual_speaker = track_display_names[lip_tracks[0]]
            if visual_speaker != audio_speaker:
                review_reason = "speaker_conflict"
                recommended_action = "relabel_to_visual_speaker"
                suggested_speaker = visual_speaker
        elif not visible_tracks:
            review_reason = "offscreen_or_missing_camera"
            recommended_action = "verify_audio_only_segment"
        elif len(visible_tracks) >= 3 and not lip_tracks:
            review_reason = "crowded_frame"
            recommended_action = "manual_visual_review"

        if review_reason is not None:
            rows.append(
                {
                    "segment_id": turn["segment_id"],
                    "start": f"{start:.2f}",
                    "end": f"{end:.2f}",
                    "audio_speaker": audio_speaker,
                    "review_reason": review_reason,
                    "recommended_action": recommended_action,
                    "suggested_speaker": suggested_speaker,
                }
            )
    return rows


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    with OUT.open("r", encoding="utf-8", newline="") as handle:
        got = list(csv.DictReader(handle))
    assert got == expected_rows()


if __name__ == "__main__":
    main()
