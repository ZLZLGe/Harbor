import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("NARRATION_AUDIT_PATH", "/root/narration_audit.json"))
SPEECH_PATH = Path(os.environ.get("SPEECH_EVENTS_PATH", "/root/speech_events.json"))
WINDOWS_PATH = Path(os.environ.get("SHOT_OBSERVATIONS_PATH", "/root/shot_observations.json"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def expected_results() -> list[dict]:
    events = load_json(SPEECH_PATH)["events"]
    windows = load_json(WINDOWS_PATH)["windows"]
    expected = []

    for event in events:
        start_sec = float(event["start_sec"])
        end_sec = float(event["end_sec"])
        duration = end_sec - start_sec

        aligned_motion_sec = 0.0
        no_face_sec = 0.0
        visible_no_motion_sec = 0.0
        visible_face_count = 0

        for window in windows:
            overlap_sec = overlap(start_sec, end_sec, window["start_sec"], window["end_sec"])
            if overlap_sec <= 0:
                continue

            face_count = len(window["visible_face_ids"])
            lip_count = len(window["lip_motion_face_ids"])
            visible_face_count = max(visible_face_count, face_count)

            if lip_count > 0:
                aligned_motion_sec += overlap_sec
            elif face_count == 0:
                no_face_sec += overlap_sec
            else:
                visible_no_motion_sec += overlap_sec

        if aligned_motion_sec / duration >= 0.6:
            label = "on_camera_speech"
            evidence = "aligned_lip_motion"
        elif no_face_sec / duration >= 0.6 and aligned_motion_sec == 0:
            label = "off_camera_voiceover"
            evidence = "no_visible_faces"
        else:
            label = "ambiguous"
            if aligned_motion_sec > 0 or (no_face_sec > 0 and visible_no_motion_sec > 0):
                evidence = "mixed_visual_signal"
            else:
                evidence = "visible_faces_without_lip_motion"

        expected.append(
            {
                "event_id": event["event_id"],
                "start_sec": round(start_sec, 2),
                "end_sec": round(end_sec, 2),
                "label": label,
                "visible_face_count": visible_face_count,
                "mouth_motion_evidence": evidence,
            }
        )

    return sorted(expected, key=lambda item: item["start_sec"])


def test_output_exists_and_is_json_array():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    payload = load_json(OUTPUT_PATH)
    assert isinstance(payload, list), "narration_audit.json must be a JSON array"


def test_schema_and_order():
    payload = load_json(OUTPUT_PATH)
    events = load_json(SPEECH_PATH)["events"]
    valid_event_ids = {event["event_id"] for event in events}
    required_keys = {
        "event_id",
        "start_sec",
        "end_sec",
        "label",
        "visible_face_count",
        "mouth_motion_evidence",
    }

    assert len(payload) == len(events)

    previous_start = None
    seen_event_ids = set()
    for index, item in enumerate(payload):
        assert required_keys.issubset(item.keys()), f"Item {index} is missing required keys"
        assert item["event_id"] in valid_event_ids
        assert item["event_id"] not in seen_event_ids
        assert isinstance(item["start_sec"], (int, float))
        assert isinstance(item["end_sec"], (int, float))
        assert item["start_sec"] < item["end_sec"]
        assert item["label"] in {"on_camera_speech", "off_camera_voiceover", "ambiguous"}
        assert isinstance(item["visible_face_count"], int)
        assert item["mouth_motion_evidence"] in {
            "aligned_lip_motion",
            "no_visible_faces",
            "visible_faces_without_lip_motion",
            "mixed_visual_signal",
        }
        if previous_start is not None:
            assert item["start_sec"] >= previous_start
        previous_start = item["start_sec"]
        seen_event_ids.add(item["event_id"])


def test_matches_expected_audit():
    payload = load_json(OUTPUT_PATH)
    expected = expected_results()

    assert payload == expected
