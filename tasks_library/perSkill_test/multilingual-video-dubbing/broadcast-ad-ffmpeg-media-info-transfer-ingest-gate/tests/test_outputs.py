import json
import os
import subprocess


MANIFEST_PATH = "/root/ingest_requirements.json"
REPORT_PATH = "/root/ad_ingest_report.json"


def round3(value):
    return round(float(value) + 1e-9, 3)


def parse_rate(value):
    numerator, denominator = value.split("/")
    denominator_value = float(denominator)
    if denominator_value == 0:
        return 0.0
    return float(numerator) / denominator_value


def infer_layout(audio_stream):
    layout = audio_stream.get("channel_layout")
    if layout:
        return layout
    channels = int(audio_stream["channels"])
    if channels == 1:
        return "mono"
    if channels == 2:
        return "stereo"
    return f"{channels} channels"


def probe_media(path):
    data = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,channels,channel_layout",
                "-of",
                "json",
                path,
            ],
            text=True,
        )
    )
    video_stream = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in data["streams"] if stream["codec_type"] == "audio")
    return {
        "duration_sec": float(data["format"]["duration"]),
        "video_codec": video_stream["codec_name"],
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "frame_rate_fps": parse_rate(video_stream["avg_frame_rate"]),
        "audio_codec": audio_stream["codec_name"],
        "audio_channel_layout": infer_layout(audio_stream),
    }


def failure_reasons(meta, requirements):
    reasons = []

    if abs(meta["duration_sec"] - requirements["duration_sec"]) > requirements["duration_tolerance_sec"]:
        reasons.append(
            f"duration_sec expected {requirements['duration_sec']:.3f} got {round3(meta['duration_sec']):.3f}"
        )
    if meta["width"] != requirements["width"] or meta["height"] != requirements["height"]:
        reasons.append(
            f"resolution expected {requirements['width']}x{requirements['height']} got {meta['width']}x{meta['height']}"
        )
    if abs(meta["frame_rate_fps"] - requirements["frame_rate_fps"]) > requirements["frame_rate_tolerance_fps"]:
        reasons.append(
            f"frame_rate_fps expected {requirements['frame_rate_fps']:.3f} got {round3(meta['frame_rate_fps']):.3f}"
        )
    if meta["video_codec"] != requirements["video_codec"]:
        reasons.append(
            f"video_codec expected {requirements['video_codec']} got {meta['video_codec']}"
        )
    if meta["audio_codec"] != requirements["audio_codec"]:
        reasons.append(
            f"audio_codec expected {requirements['audio_codec']} got {meta['audio_codec']}"
        )
    if meta["audio_channel_layout"] != requirements["audio_channel_layout"]:
        reasons.append(
            f"audio_channel_layout expected {requirements['audio_channel_layout']} got {meta['audio_channel_layout']}"
        )

    return reasons


def expected_report():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    requirements = manifest["requirements"]
    accepted = []
    rejected = []

    for relative_path in manifest["candidates"]:
        absolute_path = os.path.join("/root", relative_path)
        meta = probe_media(absolute_path)
        reasons = failure_reasons(meta, requirements)
        if reasons:
            rejected.append({"file": absolute_path, "reasons": reasons})
        else:
            accepted.append((absolute_path, meta))

    rejected.sort(key=lambda item: item["file"])
    assert len(accepted) == 1, "Fixture must contain exactly one ingest-approved candidate"

    accepted_file, accepted_meta = accepted[0]
    return {
        "campaign_id": manifest["campaign_id"],
        "station_id": manifest["station_id"],
        "spec_version": manifest["spec_version"],
        "decision": "accept_single_version",
        "accepted_file": accepted_file,
        "accepted_summary": {
            "duration_sec": round3(accepted_meta["duration_sec"]),
            "video_codec": accepted_meta["video_codec"],
            "width": accepted_meta["width"],
            "height": accepted_meta["height"],
            "frame_rate_fps": round3(accepted_meta["frame_rate_fps"]),
            "audio_codec": accepted_meta["audio_codec"],
            "audio_channel_layout": accepted_meta["audio_channel_layout"],
        },
        "reviewed_candidate_count": len(manifest["candidates"]),
        "rejected_file_count": len(rejected),
        "rejected_files": rejected,
    }


def test_report_exists():
    assert os.path.exists(REPORT_PATH), "Missing /root/ad_ingest_report.json"


def test_report_matches_expected_ingest_decision():
    with open(REPORT_PATH, "r", encoding="utf-8") as fh:
        actual = json.load(fh)

    expected = expected_report()
    assert actual == expected
