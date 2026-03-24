import json
import os
import subprocess


MANIFEST_PATH = "/root/package_manifest.json"
REPORT_PATH = "/root/dub_qc_report.json"


def round3(value):
    return round(float(value) + 1e-9, 3)


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def ffprobe_json(path, entries, select_streams=None):
    cmd = ["ffprobe", "-v", "error", "-of", "json"]
    if select_streams:
        cmd.extend(["-select_streams", select_streams])
    cmd.extend(["-show_entries", entries, path])
    return json.loads(subprocess.check_output(cmd, text=True))


def get_format_duration(path):
    data = ffprobe_json(path, "format=duration")
    return float(data["format"]["duration"])


def get_audio_stream(path):
    data = ffprobe_json(
        path,
        "stream=codec_name,sample_rate,channels:stream_tags=language",
        "a:0",
    )
    return data["streams"][0]


def test_report_exists():
    assert os.path.exists(REPORT_PATH), "Missing /root/dub_qc_report.json"


def test_report_matches_delivery_package():
    manifest = read_json(MANIFEST_PATH)
    report = read_json(REPORT_PATH)

    video_path = os.path.join("/root", manifest["video_file"])
    video_audio = get_audio_stream(video_path)
    video_duration = round3(get_format_duration(video_path))
    video_duration_delta = round3(video_duration - manifest["expected_video_duration_sec"])

    assert report["package_id"] == manifest["package_id"]
    assert report["video_file"] == video_path
    assert report["source_language"] == manifest["source_language"]
    assert report["target_language"] == manifest["target_language"]
    assert report["video_duration_sec"] == video_duration
    assert report["expected_video_duration_sec"] == round3(manifest["expected_video_duration_sec"])
    assert report["video_duration_delta_sec"] == video_duration_delta
    assert report["allowed_video_duration_delta_sec"] == round3(manifest["allowed_video_duration_delta_sec"])

    assert report["dubbed_audio"] == {
        "codec_name": video_audio["codec_name"],
        "sample_rate_hz": int(video_audio["sample_rate"]),
        "channels": int(video_audio["channels"]),
        "language_tag": video_audio.get("tags", {}).get("language", "und"),
    }

    expected_segments = []
    all_segment_audio_specs_ok = True
    all_segments_within_tolerance = True

    for entry in manifest["segments"]:
        segment_path = os.path.join("/root", entry["file"])
        segment_audio = get_audio_stream(segment_path)
        duration_sec = round3(get_format_duration(segment_path))
        expected_start_sec = round3(entry["expected_start_sec"])
        placed_start_sec = round3(entry["placed_start_sec"])
        expected_end_sec = round3(entry["expected_end_sec"])
        placed_end_sec = round3(placed_start_sec + duration_sec)
        start_drift_sec = round3(placed_start_sec - expected_start_sec)
        end_drift_sec = round3(placed_end_sec - expected_end_sec)
        sample_rate_hz = int(segment_audio["sample_rate"])
        channels = int(segment_audio["channels"])
        sample_rate_ok = sample_rate_hz == int(manifest["required_audio_sample_rate_hz"])
        channels_ok = channels == int(manifest["required_audio_channels"])
        within_tolerance = (
            sample_rate_ok
            and channels_ok
            and abs(start_drift_sec) <= float(manifest["allowed_start_drift_sec"])
            and abs(end_drift_sec) <= float(manifest["allowed_end_drift_sec"])
        )

        all_segment_audio_specs_ok = all_segment_audio_specs_ok and sample_rate_ok and channels_ok
        all_segments_within_tolerance = all_segments_within_tolerance and within_tolerance

        expected_segments.append(
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
                "audio_channels": channels,
                "sample_rate_ok": sample_rate_ok,
                "channels_ok": channels_ok,
                "within_tolerance": within_tolerance,
            }
        )

    expected_checks = {
        "video_duration_ok": abs(video_duration_delta) <= float(manifest["allowed_video_duration_delta_sec"]),
        "sample_rate_ok": int(video_audio["sample_rate"]) == int(manifest["required_audio_sample_rate_hz"]),
        "channels_ok": int(video_audio["channels"]) == int(manifest["required_audio_channels"]),
        "language_tag_ok": video_audio.get("tags", {}).get("language") == manifest["required_audio_language_tag"],
        "all_segment_audio_specs_ok": all_segment_audio_specs_ok,
        "all_segments_within_tolerance": all_segments_within_tolerance,
        "package_passes": True,
    }

    assert report["delivery_checks"] == expected_checks
    assert report["segments"] == expected_segments
    assert report["delivery_checks"]["package_passes"] is True
