#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import subprocess


BATCH_PATH = "/root/evidence_batch.json"
OUTPUT_PATH = "/root/evidence_clip_audit.json"


def round3(value):
    rounded = round(float(value), 3)
    if rounded == -0.0:
        return 0.0
    return rounded


def probe_media(path):
    payload = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,format_name:stream=index,codec_type,codec_name,width,height",
                "-of",
                "json",
                path,
            ],
            text=True,
        )
    )
    streams = payload["streams"]
    video_stream = next(stream for stream in streams if stream["codec_type"] == "video")
    audio_streams = [stream for stream in streams if stream["codec_type"] == "audio"]
    first_audio = audio_streams[0] if audio_streams else None
    return {
        "container_format": payload["format"]["format_name"],
        "duration_sec": float(payload["format"]["duration"]),
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "video_codec": video_stream["codec_name"],
        "audio_track_count": len(audio_streams),
        "audio_codec": first_audio["codec_name"] if first_audio else None,
    }


with open(BATCH_PATH, "r", encoding="utf-8") as handle:
    batch = json.load(handle)

expected_duration = float(batch["expected_duration_sec"])
duration_tolerance = float(batch["duration_tolerance_sec"])
priority = {role: index for index, role in enumerate(batch["preferred_device_order"])}

clips = []

for entry in batch["clips"]:
    absolute_path = f"/root/{entry['file']}"
    meta = probe_media(absolute_path)
    duration_delta = meta["duration_sec"] - expected_duration
    anomalies = []

    if meta["audio_track_count"] == 0:
        anomalies.append("missing_audio_track")
    if meta["width"] != int(batch["required_width"]) or meta["height"] != int(batch["required_height"]):
        anomalies.append("unexpected_resolution")
    if abs(duration_delta) > duration_tolerance:
        anomalies.append("duration_out_of_range")
    if meta["video_codec"] != batch["required_video_codec"]:
        anomalies.append("disallowed_codec")
    elif meta["audio_track_count"] > 0 and meta["audio_codec"] != batch["required_audio_codec"]:
        anomalies.append("disallowed_codec")

    clips.append(
        {
            "file": absolute_path,
            "device_role": entry["device_role"],
            "container_format": meta["container_format"],
            "duration_sec": round3(meta["duration_sec"]),
            "duration_delta_sec": round3(duration_delta),
            "width": meta["width"],
            "height": meta["height"],
            "video_codec": meta["video_codec"],
            "audio_track_count": meta["audio_track_count"],
            "audio_codec": meta["audio_codec"],
            "eligible_for_submission": len(anomalies) == 0,
            "submission_rank": 0,
            "anomalies": anomalies,
        }
    )

eligible = sorted(
    [clip for clip in clips if clip["eligible_for_submission"]],
    key=lambda clip: (
        priority[clip["device_role"]],
        abs(clip["duration_delta_sec"]),
        clip["file"],
    ),
)

for rank, clip in enumerate(eligible, start=1):
    clip["submission_rank"] = rank

clips.sort(key=lambda clip: clip["file"])

report = {
    "case_id": batch["case_id"],
    "incident_label": batch["incident_label"],
    "submission_target": batch["submission_target"],
    "recommended_submission_file": eligible[0]["file"],
    "technical_audit_summary": {
        "total_files": len(clips),
        "submission_ready_files": len(eligible),
        "missing_audio_files": sum("missing_audio_track" in clip["anomalies"] for clip in clips),
        "resolution_anomaly_files": sum("unexpected_resolution" in clip["anomalies"] for clip in clips),
        "duration_anomaly_files": sum("duration_out_of_range" in clip["anomalies"] for clip in clips),
        "codec_policy_violation_files": sum("disallowed_codec" in clip["anomalies"] for clip in clips),
    },
    "clips": clips,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
PY
