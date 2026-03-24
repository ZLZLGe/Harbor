import hashlib
import json
import os
import subprocess

import numpy as np


INPUT_VIDEO = "/root/lobby_camera.mp4"
SCHEDULE_JSON = "/root/redaction_schedule.json"
OUTPUT_VIDEO = "/outputs/privacy-redaction-review.mp4"
SCORE_JSON = "/logs/verifier/score.json"


def run(cmd):
    return subprocess.check_output(cmd, text=True)


def ffprobe_json(path):
    return json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                path,
            ]
        )
    )


def parse_ratio(value):
    numerator, denominator = value.split("/")
    return float(numerator) / float(denominator)


def save_score(metrics):
    os.makedirs(os.path.dirname(SCORE_JSON), exist_ok=True)
    current = {}
    if os.path.exists(SCORE_JSON):
        try:
            with open(SCORE_JSON, "r", encoding="utf-8") as fh:
                current = json.load(fh)
        except Exception:
            current = {}
    current.update(metrics)
    with open(SCORE_JSON, "w", encoding="utf-8") as fh:
        json.dump(current, fh, indent=2, sort_keys=True)


def pcm_md5(path):
    audio_bytes = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            path,
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ]
    )
    return hashlib.md5(audio_bytes).hexdigest()


def build_expected_filter():
    with open(SCHEDULE_JSON, "r", encoding="utf-8") as fh:
        schedule = json.load(fh)

    meta = ffprobe_json(INPUT_VIDEO)
    video_stream = next(stream for stream in meta["streams"] if stream["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    duration = float(meta["format"]["duration"])

    def expr(intervals):
        return "+".join(
            f"between(t,{start:.3f},{end:.3f})"
            for start, end in intervals
        )

    regions = schedule["regions"]
    split_labels = ["base_src"] + [f"r{idx}src" for idx in range(len(regions))]
    filter_parts = [
        f"[0:v]split={len(split_labels)}{''.join(f'[{label}]' for label in split_labels)}",
        f"color=c=black@{float(schedule['dim_alpha'])}:s={width}x{height}:d={duration:.3f}[shade]",
    ]

    all_intervals = []
    for region in regions:
        all_intervals.extend(region["intervals"])

    filter_parts.append(
        f"[base_src][shade]overlay=0:0:enable='{expr(all_intervals)}'[v0]"
    )

    current_label = "v0"
    for index, region in enumerate(regions):
        region_label = f"r{index}"
        output_label = "v" if index == len(regions) - 1 else f"v{index + 1}"
        filter_parts.append(
            f"[{region_label}src]crop={region['w']}:{region['h']}:{region['x']}:{region['y']},"
            f"gblur=sigma=18:steps=2[{region_label}]"
        )
        filter_parts.append(
            f"[{current_label}][{region_label}]overlay={region['x']}:{region['y']}:"
            f"enable='{expr(region['intervals'])}'[{output_label}]"
        )
        current_label = output_label

    return ";".join(filter_parts)


EXPECTED_FILTER = build_expected_filter()


def extract_frame(path, second, use_filter=False):
    cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-i",
        path,
    ]
    if use_filter:
        cmd.extend(["-filter_complex", EXPECTED_FILTER, "-map", "[v]"])
    cmd.extend(
        [
            "-ss",
            f"{second:.3f}",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    raw = subprocess.check_output(cmd)
    meta = ffprobe_json(INPUT_VIDEO if use_filter else path)
    video_stream = next(stream for stream in meta["streams"] if stream["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    return np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))


def assert_frame_matches(second, expected_source):
    actual = extract_frame(OUTPUT_VIDEO, second, use_filter=False)
    expected = extract_frame(expected_source, second, use_filter=(expected_source == INPUT_VIDEO))
    diff = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
    mae = float(diff.mean())
    p99 = float(np.percentile(diff, 99))
    save_score({
        f"frame_{second:.1f}_mae": mae,
        f"frame_{second:.1f}_p99": p99,
    })
    assert mae <= 6.0
    assert p99 <= 40.0


class TestPrivacyRedactionReview:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_VIDEO), "缺少 /outputs/privacy-redaction-review.mp4"

    def test_video_shape_duration_and_audio_presence(self):
        input_meta = ffprobe_json(INPUT_VIDEO)
        output_meta = ffprobe_json(OUTPUT_VIDEO)

        input_video_stream = next(stream for stream in input_meta["streams"] if stream["codec_type"] == "video")
        output_video_stream = next(stream for stream in output_meta["streams"] if stream["codec_type"] == "video")
        output_audio_stream = next(stream for stream in output_meta["streams"] if stream["codec_type"] == "audio")

        assert int(output_video_stream["width"]) == int(input_video_stream["width"])
        assert int(output_video_stream["height"]) == int(input_video_stream["height"])
        assert abs(parse_ratio(output_video_stream["avg_frame_rate"]) - parse_ratio(input_video_stream["avg_frame_rate"])) <= 0.01
        assert abs(float(output_meta["format"]["duration"]) - float(input_meta["format"]["duration"])) <= 0.05
        assert output_audio_stream["codec_type"] == "audio"

    def test_audio_is_preserved_exactly(self):
        input_audio_md5 = pcm_md5(INPUT_VIDEO)
        output_audio_md5 = pcm_md5(OUTPUT_VIDEO)
        save_score({"input_audio_md5": input_audio_md5, "output_audio_md5": output_audio_md5})
        assert output_audio_md5 == input_audio_md5, "输出音频和输入音频不一致"

    def test_non_redacted_window_matches_input(self):
        assert_frame_matches(5.8, INPUT_VIDEO)

    def test_single_region_redaction_matches_spec(self):
        assert_frame_matches(1.5, INPUT_VIDEO)

    def test_two_region_redaction_matches_spec(self):
        assert_frame_matches(3.0, INPUT_VIDEO)

    def test_late_redaction_matches_spec(self):
        assert_frame_matches(7.6, INPUT_VIDEO)
