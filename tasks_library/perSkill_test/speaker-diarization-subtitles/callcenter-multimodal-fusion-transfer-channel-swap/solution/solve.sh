#!/bin/bash
set -e

python3 <<'PY'
import json
import os
from pathlib import Path

MANIFEST_PATH = Path(os.environ.get("SESSION_MANIFEST_PATH", "/root/session_manifest.json"))
AUDIO_PATH = Path(os.environ.get("AUDIO_ACTIVITY_WINDOWS_PATH", "/root/audio_activity_windows.json"))
VISUAL_PATH = Path(os.environ.get("SPLIT_SCREEN_OBSERVATIONS_PATH", "/root/split_screen_observations.json"))
OUTPUT_PATH = Path(os.environ.get("CHANNEL_SWAP_ALERTS_PATH", "/root/channel_swap_alerts.json"))


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
            "window_id": audio["window_id"],
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

payload = {
    "session_id": manifest["session_id"],
    "alerts": alerts,
}

with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
