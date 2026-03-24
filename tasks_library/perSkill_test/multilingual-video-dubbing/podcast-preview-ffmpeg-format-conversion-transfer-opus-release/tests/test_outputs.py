import json
import os
import subprocess
import tempfile

import numpy as np


INPUT_WAV = "/root/podcast_preview_master.wav"
OUTPUT_OPUS = "/outputs/podcast_preview.opus"


def ffprobe_json(path):
    result = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            path,
        ],
        text=True,
    )
    return json.loads(result)


def decode_audio_stereo_48k(path, temp_dir, name):
    wav_path = os.path.join(temp_dir, name)
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            path,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            wav_path,
        ]
    )
    pcm = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            wav_path,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ]
    )
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32)


def normalized_correlation(a, b):
    size = min(len(a), len(b))
    if size == 0:
        raise AssertionError("Decoded audio is empty")
    a = a[:size]
    b = b[:size]
    a = a - np.mean(a)
    b = b - np.mean(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        raise AssertionError("Audio correlation denominator is zero")
    return float(np.dot(a, b) / denom)


class TestPodcastPreviewOpusRelease:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_OPUS), "缺少 /outputs/podcast_preview.opus"

    def test_codec_sample_rate_and_channels(self):
        info = ffprobe_json(OUTPUT_OPUS)
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]

        assert len(audio_streams) == 1, "输出应只有一条音频流"
        stream = audio_streams[0]
        assert stream["codec_name"] == "opus", "音频编码必须为 Opus"
        assert stream["sample_rate"] == "48000", "采样率必须为 48000 Hz"
        assert int(stream["channels"]) == 2, "输出必须保持双声道"

    def test_bitrate_matches_release_target(self):
        info = ffprobe_json(OUTPUT_OPUS)
        bit_rate = int(info["format"]["bit_rate"])
        assert 56000 <= bit_rate <= 76000, f"平均比特率异常: {bit_rate} bps"

    def test_duration_matches_master(self):
        source = ffprobe_json(INPUT_WAV)
        output = ffprobe_json(OUTPUT_OPUS)
        source_duration = float(source["format"]["duration"])
        output_duration = float(output["format"]["duration"])

        assert abs(output_duration - source_duration) <= 0.12, (
            f"输出时长 {output_duration:.3f}s 与输入 {source_duration:.3f}s 偏差过大"
        )

    def test_audio_content_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reference = decode_audio_stereo_48k(INPUT_WAV, temp_dir, "reference.wav")
            output = decode_audio_stereo_48k(OUTPUT_OPUS, temp_dir, "output.wav")

        correlation = normalized_correlation(reference, output)
        assert correlation >= 0.95, f"输出音频与输入内容偏差过大，相关系数={correlation:.4f}"
