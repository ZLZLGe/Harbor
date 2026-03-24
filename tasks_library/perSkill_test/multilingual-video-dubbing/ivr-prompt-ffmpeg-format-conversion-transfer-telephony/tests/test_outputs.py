import json
import os
import subprocess
import tempfile

import numpy as np


INPUT_WAV = "/root/ivr_prompt_master.wav"
OUTPUT_WAV = "/outputs/ivr_prompt.wav"


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


def decode_audio_8k_mono(path, temp_dir, name):
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
            "1",
            "-ar",
            "8000",
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


class TestIvrPromptTelephonyPackaging:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_WAV), "缺少 /outputs/ivr_prompt.wav"

    def test_container_codec_and_channels(self):
        info = ffprobe_json(OUTPUT_WAV)
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]

        assert "wav" in info["format"]["format_name"], "输出容器必须是 WAV"
        assert len(audio_streams) == 1, "输出应只有一条音频流"

        stream = audio_streams[0]
        assert stream["codec_name"] == "pcm_mulaw", "音频编码必须为 G.711 mu-law"
        assert stream["sample_rate"] == "8000", "采样率必须为 8000 Hz"
        assert int(stream["channels"]) == 1, "输出必须为单声道"

    def test_duration_matches_master(self):
        source = ffprobe_json(INPUT_WAV)
        output = ffprobe_json(OUTPUT_WAV)
        source_duration = float(source["format"]["duration"])
        output_duration = float(output["format"]["duration"])

        assert abs(output_duration - source_duration) <= 0.05, (
            f"输出时长 {output_duration:.3f}s 与输入 {source_duration:.3f}s 偏差过大"
        )

    def test_audio_content_is_preserved_after_decode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reference = decode_audio_8k_mono(INPUT_WAV, temp_dir, "reference.wav")
            output = decode_audio_8k_mono(OUTPUT_WAV, temp_dir, "output.wav")

        correlation = normalized_correlation(reference, output)
        assert correlation >= 0.97, f"输出语音内容偏差过大，相关系数={correlation:.4f}"
