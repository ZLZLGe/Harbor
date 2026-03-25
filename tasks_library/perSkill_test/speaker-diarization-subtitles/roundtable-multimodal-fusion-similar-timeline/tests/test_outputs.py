import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("SPEAKER_TIMELINE_PATH", "/root/speaker_timeline.json"))
AUDIO_PATH = Path(os.environ.get("AUDIO_CANDIDATES_PATH", "/root/audio_turn_candidates.json"))
VISUAL_PATH = Path(os.environ.get("VISUAL_WINDOWS_PATH", "/root/visual_windows.json"))
AFFINITY_PATH = Path(os.environ.get("CLUSTER_FACE_AFFINITY_PATH", "/root/cluster_face_affinity.json"))
ROSTER_PATH = Path(os.environ.get("SPEAKER_ROSTER_PATH", "/root/speaker_roster.json"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def best_speaker(cluster_name: str, affinity_table: dict, allowed_speakers: set[str]) -> str:
    speaker_id = max(affinity_table[cluster_name], key=affinity_table[cluster_name].get)
    assert speaker_id in allowed_speakers
    return speaker_id


def midpoint_window(start_sec: float, end_sec: float, windows: list[dict]) -> dict:
    midpoint = (start_sec + end_sec) / 2.0
    for window in windows:
        if window["start_sec"] <= midpoint < window["end_sec"]:
            return window
    if midpoint == windows[-1]["end_sec"]:
        return windows[-1]
    raise AssertionError(f"No visual window covers midpoint {midpoint}")


def confidence_for(window: dict, speaker_id: str) -> str:
    if window.get("active_face_id") == speaker_id:
        return "high"
    if speaker_id in window["visible_face_ids"]:
        return "medium"
    return "low"


def expected_timeline() -> list[dict]:
    audio_candidates = load_json(AUDIO_PATH)["candidates"]
    visual_windows = load_json(VISUAL_PATH)["windows"]
    affinity_table = load_json(AFFINITY_PATH)
    allowed_speakers = {
        item["speaker_id"]
        for item in load_json(ROSTER_PATH)["speakers"]
    }

    result = []
    for candidate in audio_candidates:
        start_sec = candidate["start_sec"]
        end_sec = candidate["end_sec"]
        if candidate["split_by_visual"]:
            for window in visual_windows:
                overlap_start = max(start_sec, window["start_sec"])
                overlap_end = min(end_sec, window["end_sec"])
                if overlap_end <= overlap_start:
                    continue
                speaker_id = window.get("active_face_id") or best_speaker(
                    candidate["audio_cluster"], affinity_table, allowed_speakers
                )
                result.append(
                    build_expected_segment(overlap_start, overlap_end, speaker_id, visual_windows)
                )
        else:
            speaker_id = best_speaker(candidate["audio_cluster"], affinity_table, allowed_speakers)
            result.append(build_expected_segment(start_sec, end_sec, speaker_id, visual_windows))

    return sorted(result, key=lambda item: item["start_sec"])


def build_expected_segment(start_sec: float, end_sec: float, speaker_id: str, visual_windows: list[dict]) -> dict:
    window = midpoint_window(start_sec, end_sec, visual_windows)
    return {
        "speaker_id": speaker_id,
        "start_sec": round(start_sec, 2),
        "end_sec": round(end_sec, 2),
        "visible_face_count": len(window["visible_face_ids"]),
        "lip_motion_confirmed": window.get("active_face_id") == speaker_id,
        "visual_confidence": confidence_for(window, speaker_id),
    }


def test_output_exists_and_is_json_array():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    payload = load_json(OUTPUT_PATH)
    assert isinstance(payload, list), "speaker_timeline.json must be a JSON array"


def test_schema_and_order():
    payload = load_json(OUTPUT_PATH)
    allowed_speakers = {
        item["speaker_id"]
        for item in load_json(ROSTER_PATH)["speakers"]
    }
    previous_end = None
    required_keys = {
        "speaker_id",
        "start_sec",
        "end_sec",
        "visible_face_count",
        "lip_motion_confirmed",
        "visual_confidence",
    }

    for index, item in enumerate(payload):
        assert required_keys.issubset(item.keys()), f"Segment {index} is missing required keys"
        assert item["speaker_id"] in allowed_speakers
        assert isinstance(item["start_sec"], (int, float))
        assert isinstance(item["end_sec"], (int, float))
        assert item["start_sec"] < item["end_sec"]
        assert isinstance(item["visible_face_count"], int)
        assert isinstance(item["lip_motion_confirmed"], bool)
        assert item["visual_confidence"] in {"high", "medium", "low"}
        if previous_end is not None:
            assert item["start_sec"] >= previous_end
        previous_end = item["end_sec"]


def test_matches_expected_timeline():
    payload = load_json(OUTPUT_PATH)
    expected = expected_timeline()
    assert len(payload) == len(expected)

    for actual, target in zip(payload, expected):
        assert actual["speaker_id"] == target["speaker_id"]
        assert abs(actual["start_sec"] - target["start_sec"]) <= 0.01
        assert abs(actual["end_sec"] - target["end_sec"]) <= 0.01
        assert actual["visible_face_count"] == target["visible_face_count"]
        assert actual["lip_motion_confirmed"] == target["lip_motion_confirmed"]
        assert actual["visual_confidence"] == target["visual_confidence"]
