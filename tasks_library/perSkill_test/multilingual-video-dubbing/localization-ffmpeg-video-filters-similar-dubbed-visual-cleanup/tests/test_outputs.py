import hashlib
import json
import os
import subprocess

import numpy as np


INPUT_VIDEO = "/root/program_with_source_subs.mp4"
WATERMARK = "/root/channel_watermark.png"
OUTPUT_VIDEO = "/outputs/dubbed-visual-cleanup.mp4"
SCORE_JSON = "/logs/verifier/score.json"
EXPECTED_FILTER = (
    "[0:v]scale=640:360,boxblur=12:1[bg];"
    "[0:v]crop=320:168:0:0,scale=640:300[fg];"
    "[bg][fg]overlay=0:0[base];"
    "[1:v]scale=150:-1[wm];"
    "[base][wm]overlay=460:22[v]"
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


def extract_frame(path, second):
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            path,
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
    return np.frombuffer(raw, dtype=np.uint8).reshape((360, 640, 3))


def extract_expected_frame(second):
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            INPUT_VIDEO,
            "-i",
            WATERMARK,
            "-ss",
            f"{second:.3f}",
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
    return np.frombuffer(raw, dtype=np.uint8).reshape((360, 640, 3))


class TestDubbedVisualCleanup:
    def test_files_exist(self):
        assert os.path.exists(OUTPUT_VIDEO), "缺少 /outputs/dubbed-visual-cleanup.mp4"

    def test_video_shape_and_duration(self):
        output_meta = ffprobe_json(OUTPUT_VIDEO)
        input_meta = ffprobe_json(INPUT_VIDEO)

        output_video_stream = next(s for s in output_meta["streams"] if s["codec_type"] == "video")
        assert int(output_video_stream["width"]) == 640
        assert int(output_video_stream["height"]) == 360

        output_duration = float(output_meta["format"]["duration"])
        input_duration = float(input_meta["format"]["duration"])
        assert abs(output_duration - input_duration) <= 0.05

    def test_audio_is_preserved_exactly(self):
        input_audio_md5 = pcm_md5(INPUT_VIDEO)
        output_audio_md5 = pcm_md5(OUTPUT_VIDEO)
        save_score({"input_audio_md5": input_audio_md5, "output_audio_md5": output_audio_md5})
        assert output_audio_md5 == input_audio_md5, "输出音频和输入节目音频不一致"

    def test_frame_matches_spec_at_1s(self):
        actual = extract_frame(OUTPUT_VIDEO, 1.0)
        expected = extract_expected_frame(1.0)
        diff = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
        mae = float(diff.mean())
        p99 = float(np.percentile(diff, 99))
        save_score({"frame_1s_mae": mae, "frame_1s_p99": p99})
        assert mae <= 6.0
        assert p99 <= 40.0

    def test_frame_matches_spec_at_8s(self):
        actual = extract_frame(OUTPUT_VIDEO, 8.0)
        expected = extract_expected_frame(8.0)
        diff = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
        mae = float(diff.mean())
        p99 = float(np.percentile(diff, 99))
        save_score({"frame_8s_mae": mae, "frame_8s_p99": p99})
        assert mae <= 6.0
        assert p99 <= 40.0
