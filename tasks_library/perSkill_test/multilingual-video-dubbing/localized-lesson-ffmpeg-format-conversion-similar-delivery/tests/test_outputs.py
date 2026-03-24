import json
import os
import subprocess
import tempfile

import numpy as np


OUTPUT_VIDEO = "/outputs/localized_lesson.mp4"
SOURCE_VIDEO = "/root/lesson_clip.mp4"
REFERENCE_AUDIO = "/root/aligned_narration.wav"


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


def extract_frame_rgb(path, second, width, height):
    frame = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-ss",
            str(second),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    return np.frombuffer(frame, dtype=np.uint8).reshape((height, width, 3))


def decode_audio_mono_48k(path, temp_dir, name):
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


class TestLocalizedLessonDelivery:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_VIDEO), "缺少 /outputs/localized_lesson.mp4"

    def test_stream_layout_and_codecs(self):
        info = ffprobe_json(OUTPUT_VIDEO)
        video_streams = [s for s in info["streams"] if s["codec_type"] == "video"]
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]

        assert len(video_streams) == 1, "输出应只有一条视频流"
        assert len(audio_streams) == 1, "输出应只有一条音频流"
        assert video_streams[0]["codec_name"] == "h264", "视频编码必须为 H.264"
        assert audio_streams[0]["codec_name"] == "aac", "音频编码必须为 AAC"
        assert audio_streams[0]["sample_rate"] == "48000", "音频采样率必须为 48000 Hz"
        assert int(audio_streams[0]["channels"]) == 1, "音频必须为单声道"

    def test_duration_and_resolution_match_source(self):
        source = ffprobe_json(SOURCE_VIDEO)
        output = ffprobe_json(OUTPUT_VIDEO)
        source_video = next(s for s in source["streams"] if s["codec_type"] == "video")
        output_video = next(s for s in output["streams"] if s["codec_type"] == "video")

        source_duration = float(source["format"]["duration"])
        output_duration = float(output["format"]["duration"])

        assert output_video["width"] == source_video["width"], "分辨率宽度不能变化"
        assert output_video["height"] == source_video["height"], "分辨率高度不能变化"
        assert abs(output_duration - source_duration) <= 0.12, "总时长应与原视频基本一致"

    def test_visual_content_is_preserved(self):
        source = ffprobe_json(SOURCE_VIDEO)
        video_stream = next(s for s in source["streams"] if s["codec_type"] == "video")
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        sample_points = [1.0, 6.0, 10.5]

        maes = []
        for second in sample_points:
            source_frame = extract_frame_rgb(SOURCE_VIDEO, second, width, height)
            output_frame = extract_frame_rgb(OUTPUT_VIDEO, second, width, height)
            maes.append(float(np.mean(np.abs(source_frame.astype(np.int16) - output_frame.astype(np.int16)))))

        assert max(maes) <= 6.0, f"画面与原视频差异过大: {maes}"

    def test_audio_matches_localized_narration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reference = decode_audio_mono_48k(REFERENCE_AUDIO, temp_dir, "reference.wav")
            output = decode_audio_mono_48k(OUTPUT_VIDEO, temp_dir, "output.wav")

        correlation = normalized_correlation(reference, output)
        assert correlation >= 0.97, f"输出音轨与给定旁白不一致，相关系数={correlation:.4f}"
