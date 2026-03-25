import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("CHANNEL_SWAP_ALERTS_PATH", "/root/channel_swap_alerts.json"))
MANIFEST_PATH = Path(os.environ.get("SESSION_MANIFEST_PATH", "/root/session_manifest.json"))
AUDIO_PATH = Path(os.environ.get("AUDIO_ACTIVITY_WINDOWS_PATH", "/root/audio_activity_windows.json"))
VISUAL_PATH = Path(os.environ.get("SPLIT_SCREEN_OBSERVATIONS_PATH", "/root/split_screen_observations.json"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def visual_state(window: dict) -> str:
    left = bool(window["left_mouth_moving"])
    right = bool(window["right_mouth_moving"])
    if left and not right:
        return "left_only"
    if right and not left:
        return "right_only"
    if left and right:
        return "both"
    return "none"


def face_visibility(values: list[bool]) -> str:
    if all(values):
        return "always_visible"
    if not any(values):
        return "never_visible"
    return "partial"


def mouth_state(values: list[bool]) -> str:
    if all(values):
        return "continuous_motion"
    if not any(values):
        return "no_motion"
    return "intermittent_motion"


def expected_payload() -> dict:
    manifest = load_json(MANIFEST_PATH)
    audio_windows = load_json(AUDIO_PATH)["windows"]
    visual_windows = {item["window_id"]: item for item in load_json(VISUAL_PATH)["windows"]}
    expected_roles = {
        side: payload["expected_role"]
        for side, payload in manifest["sides"].items()
    }
    merge_gap_sec = float(manifest["merge_gap_sec"])

    flagged = []
    for audio in audio_windows:
        visual = visual_windows[audio["window_id"]]
        state = visual_state(visual)
        audio_side = audio["audio_side_active"]
        audio_role = audio["audio_speaker_role"]

        if (
            (audio_side == "left" and state == "right_only")
            or (audio_side == "right" and state == "left_only")
        ):
            alert_type = "channel_swap"
        elif state == f"{audio_side}_only" and audio_role != expected_roles[audio_side]:
            alert_type = "role_mismatch"
        elif state in {"none", "both"} and not visual[f"{audio_side}_mouth_moving"]:
            alert_type = "cross_screen_speech"
        else:
            continue

        flagged.append(
            {
                "start_sec": float(audio["start_sec"]),
                "end_sec": float(audio["end_sec"]),
                "alert_type": alert_type,
                "audio_side_active": audio_side,
                "audio_speaker_role": audio_role,
                "left_face_visible": bool(visual["left_face_visible"]),
                "left_mouth_moving": bool(visual["left_mouth_moving"]),
                "right_face_visible": bool(visual["right_face_visible"]),
                "right_mouth_moving": bool(visual["right_mouth_moving"]),
            }
        )

    merged = []
    for item in flagged:
        if not merged:
            merged.append(
                {
                    "start_sec": item["start_sec"],
                    "end_sec": item["end_sec"],
                    "alert_type": item["alert_type"],
                    "audio_side_active": item["audio_side_active"],
                    "audio_speaker_role": item["audio_speaker_role"],
                    "windows": [item],
                }
            )
            continue

        current = merged[-1]
        gap = item["start_sec"] - current["end_sec"]
        if (
            item["alert_type"] == current["alert_type"]
            and item["audio_side_active"] == current["audio_side_active"]
            and item["audio_speaker_role"] == current["audio_speaker_role"]
            and gap <= merge_gap_sec
        ):
            current["end_sec"] = item["end_sec"]
            current["windows"].append(item)
        else:
            merged.append(
                {
                    "start_sec": item["start_sec"],
                    "end_sec": item["end_sec"],
                    "alert_type": item["alert_type"],
                    "audio_side_active": item["audio_side_active"],
                    "audio_speaker_role": item["audio_speaker_role"],
                    "windows": [item],
                }
            )

    alerts = []
    for index, item in enumerate(merged, start=1):
        windows = item["windows"]
        alerts.append(
            {
                "alert_id": f"alert_{index:02d}",
                "start_sec": round(item["start_sec"], 2),
                "end_sec": round(item["end_sec"], 2),
                "alert_type": item["alert_type"],
                "audio_side_active": item["audio_side_active"],
                "audio_speaker_role": item["audio_speaker_role"],
                "left_face_visibility": face_visibility([w["left_face_visible"] for w in windows]),
                "right_face_visibility": face_visibility([w["right_face_visible"] for w in windows]),
                "left_mouth_state": mouth_state([w["left_mouth_moving"] for w in windows]),
                "right_mouth_state": mouth_state([w["right_mouth_moving"] for w in windows]),
            }
        )

    return {
        "session_id": manifest["session_id"],
        "alerts": alerts,
    }


def test_output_exists_and_top_level_contract():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    payload = load_json(OUTPUT_PATH)
    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"session_id", "alerts"}
    assert isinstance(payload["session_id"], str)
    assert isinstance(payload["alerts"], list)


def test_alert_schema_and_order():
    payload = load_json(OUTPUT_PATH)
    valid_alert_types = {"channel_swap", "role_mismatch", "cross_screen_speech"}
    valid_sides = {"left", "right"}
    valid_roles = {"agent", "customer"}
    valid_face_visibility = {"always_visible", "partial", "never_visible"}
    valid_mouth_states = {"continuous_motion", "intermittent_motion", "no_motion"}

    previous_start = None
    for index, alert in enumerate(payload["alerts"], start=1):
        assert set(alert.keys()) == {
            "alert_id",
            "start_sec",
            "end_sec",
            "alert_type",
            "audio_side_active",
            "audio_speaker_role",
            "left_face_visibility",
            "right_face_visibility",
            "left_mouth_state",
            "right_mouth_state",
        }
        assert alert["alert_id"] == f"alert_{index:02d}"
        assert isinstance(alert["start_sec"], (int, float))
        assert isinstance(alert["end_sec"], (int, float))
        assert alert["end_sec"] > alert["start_sec"]
        assert alert["alert_type"] in valid_alert_types
        assert alert["audio_side_active"] in valid_sides
        assert alert["audio_speaker_role"] in valid_roles
        assert alert["left_face_visibility"] in valid_face_visibility
        assert alert["right_face_visibility"] in valid_face_visibility
        assert alert["left_mouth_state"] in valid_mouth_states
        assert alert["right_mouth_state"] in valid_mouth_states
        if previous_start is not None:
            assert alert["start_sec"] >= previous_start
        previous_start = alert["start_sec"]


def test_matches_expected_alerts():
    payload = load_json(OUTPUT_PATH)
    assert payload == expected_payload()
