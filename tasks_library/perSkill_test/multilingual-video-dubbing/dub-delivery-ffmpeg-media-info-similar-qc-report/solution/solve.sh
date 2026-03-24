#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import subprocess

MANIFEST_PATH = "/root/package_manifest.json"
OUTPUT_PATH = "/root/dub_qc_report.json"


def round3(value: float) -> float:
    return round(float(value) + 1e-9, 3)


def ffprobe_json(path: str, entries: str, select_streams: str | None = None) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-of",
        "json",
    ]
    if select_streams:
        cmd.extend(["-select_streams", select_streams])
    cmd.extend(["-show_entries", entries, path])
    return json.loads(subprocess.check_output(cmd, text=True))


def get_format_duration(path: str) -> float:
    data = ffprobe_json(path, "format=duration")
    return float(data["format"]["duration"])


def get_audio_stream(path: str) -> dict:
    data = ffprobe_json(
        path,
        "stream=codec_name,sample_rate,channels:stream_tags=language",
        "a:0",
    )
    return data["streams"][0]


with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
    manifest = json.load(fh)

video_path = os.path.join("/root", manifest["video_file"])
video_duration = round3(get_format_duration(video_path))
video_duration_delta = round3(video_duration - manifest["expected_video_duration_sec"])
video_audio = get_audio_stream(video_path)

required_sample_rate = int(manifest["required_audio_sample_rate_hz"])
required_channels = int(manifest["required_audio_channels"])
required_language_tag = manifest["required_audio_language_tag"]
allowed_start_drift = float(manifest["allowed_start_drift_sec"])
allowed_end_drift = float(manifest["allowed_end_drift_sec"])

segments = []
all_segment_audio_specs_ok = True
all_segments_within_tolerance = True

for entry in manifest["segments"]:
    segment_path = os.path.join("/root", entry["file"])
    segment_audio = get_audio_stream(segment_path)
    duration_sec = round3(get_format_duration(segment_path))
    placed_start_sec = round3(entry["placed_start_sec"])
    expected_start_sec = round3(entry["expected_start_sec"])
    expected_end_sec = round3(entry["expected_end_sec"])
    placed_end_sec = round3(placed_start_sec + duration_sec)
    start_drift_sec = round3(placed_start_sec - expected_start_sec)
    end_drift_sec = round3(placed_end_sec - expected_end_sec)
    sample_rate_hz = int(segment_audio["sample_rate"])
    audio_channels = int(segment_audio["channels"])
    sample_rate_ok = sample_rate_hz == required_sample_rate
    channels_ok = audio_channels == required_channels
    within_tolerance = (
        sample_rate_ok
        and channels_ok
        and abs(start_drift_sec) <= allowed_start_drift
        and abs(end_drift_sec) <= allowed_end_drift
    )

    all_segment_audio_specs_ok = all_segment_audio_specs_ok and sample_rate_ok and channels_ok
    all_segments_within_tolerance = all_segments_within_tolerance and within_tolerance

    segments.append(
        {
            "segment_id": entry["segment_id"],
            "segment_file": segment_path,
            "expected_start_sec": expected_start_sec,
            "placed_start_sec": placed_start_sec,
            "expected_end_sec": expected_end_sec,
            "placed_end_sec": placed_end_sec,
            "duration_sec": duration_sec,
            "start_drift_sec": start_drift_sec,
            "end_drift_sec": end_drift_sec,
            "audio_sample_rate_hz": sample_rate_hz,
            "audio_channels": audio_channels,
            "sample_rate_ok": sample_rate_ok,
            "channels_ok": channels_ok,
            "within_tolerance": within_tolerance,
        }
    )

delivery_checks = {
    "video_duration_ok": abs(video_duration_delta) <= float(manifest["allowed_video_duration_delta_sec"]),
    "sample_rate_ok": int(video_audio["sample_rate"]) == required_sample_rate,
    "channels_ok": int(video_audio["channels"]) == required_channels,
    "language_tag_ok": video_audio.get("tags", {}).get("language") == required_language_tag,
    "all_segment_audio_specs_ok": all_segment_audio_specs_ok,
    "all_segments_within_tolerance": all_segments_within_tolerance,
}
delivery_checks["package_passes"] = all(delivery_checks.values())

report = {
    "package_id": manifest["package_id"],
    "video_file": video_path,
    "source_language": manifest["source_language"],
    "target_language": manifest["target_language"],
    "video_duration_sec": video_duration,
    "expected_video_duration_sec": round3(manifest["expected_video_duration_sec"]),
    "video_duration_delta_sec": video_duration_delta,
    "allowed_video_duration_delta_sec": round3(manifest["allowed_video_duration_delta_sec"]),
    "dubbed_audio": {
        "codec_name": video_audio["codec_name"],
        "sample_rate_hz": int(video_audio["sample_rate"]),
        "channels": int(video_audio["channels"]),
        "language_tag": video_audio.get("tags", {}).get("language", "und"),
    },
    "delivery_checks": delivery_checks,
    "segments": segments,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2)
    fh.write("\n")
PY
