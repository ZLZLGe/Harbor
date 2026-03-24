import json
import os
import subprocess

import numpy as np


INPUT_VIDEO = "/root/practice_review_feed.mp4"
LOGO = "/root/coaching_bug.png"
SPEC_JSON = "/root/replay_spec.json"
OUTPUT_VIDEO = "/outputs/coaching-replay.mp4"
SCORE_JSON = "/logs/verifier/score.json"


with open(SPEC_JSON, "r", encoding="utf-8") as fh:
    SPEC = json.load(fh)


EXPECTED_DURATION = (
    (SPEC["segment_end_sec"] - SPEC["segment_start_sec"]) * SPEC["slowdown_factor"]
)
EXPECTED_FILTER = (
    f"[0:v]crop={SPEC['crop_width_expr']}:{SPEC['crop_height_expr']}:"
    f"{SPEC['crop_x_expr']}:{SPEC['crop_y_expr']},"
    f"scale={SPEC['output_width']}:{SPEC['output_height']}[base];"
    f"[1:v]scale={SPEC['logo_width']}:-1[logo];"
    f"[base][logo]overlay={SPEC['overlay_x']}:{SPEC['overlay_y']}[v]"
)


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


def extract_output_frame(second):
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-ss",
            f"{second:.3f}",
            "-i",
            OUTPUT_VIDEO,
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    return np.frombuffer(raw, dtype=np.uint8).reshape(
        (SPEC["output_height"], SPEC["output_width"], 3)
    )


def extract_expected_frame(output_second):
    source_second = SPEC["segment_start_sec"] + (
        output_second / SPEC["slowdown_factor"]
    )
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-ss",
            f"{source_second:.3f}",
            "-i",
            INPUT_VIDEO,
            "-i",
            LOGO,
            "-filter_complex",
            EXPECTED_FILTER,
            "-map",
            "[v]",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    return np.frombuffer(raw, dtype=np.uint8).reshape(
        (SPEC["output_height"], SPEC["output_width"], 3)
    )


def assert_frame_matches(second):
    actual = extract_output_frame(second)
    expected = extract_expected_frame(second)
    diff = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
    mae = float(diff.mean())
    p99 = float(np.percentile(diff, 99))
    save_score(
        {
            f"frame_{second:.1f}_mae": mae,
            f"frame_{second:.1f}_p99": p99,
        }
    )
    assert mae <= 7.0
    assert p99 <= 45.0


class TestCoachingReplay:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_VIDEO), "缺少 /outputs/coaching-replay.mp4"

    def test_video_shape_duration_and_no_audio(self):
        meta = ffprobe_json(OUTPUT_VIDEO)
        video_streams = [stream for stream in meta["streams"] if stream["codec_type"] == "video"]
        audio_streams = [stream for stream in meta["streams"] if stream["codec_type"] == "audio"]

        assert len(video_streams) == 1, "输出应只有一路视频流"
        assert len(audio_streams) == 0, "输出不应包含音频流"
        assert int(video_streams[0]["width"]) == SPEC["output_width"]
        assert int(video_streams[0]["height"]) == SPEC["output_height"]

        duration = float(meta["format"]["duration"])
        save_score({"output_duration_sec": duration, "expected_duration_sec": EXPECTED_DURATION})
        assert abs(duration - EXPECTED_DURATION) <= 0.08

    def test_frame_mapping_near_start(self):
        assert_frame_matches(0.8)

    def test_frame_mapping_mid_segment(self):
        assert_frame_matches(2.8)

    def test_frame_mapping_near_end(self):
        assert_frame_matches(5.0)
