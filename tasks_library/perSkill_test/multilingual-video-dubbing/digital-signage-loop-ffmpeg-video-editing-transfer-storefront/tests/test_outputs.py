import json
import os
import subprocess
from pathlib import Path

import numpy as np

ROOT = os.environ.get("TASK_ROOT", "/root")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/outputs")
TMP_DIR = Path(os.environ.get("TEST_TMPDIR", "/tmp/storefront-test"))

OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "storefront_loop.mp4")
PLAN_PATH = os.path.join(ROOT, "storefront_plan.json")


def run(cmd):
    subprocess.check_call(cmd)


def ffprobe_json(path):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
                "-of",
                "json",
                path,
            ],
            text=True,
        )
    )


def extract_video_signature(path, start, end, out_path):
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            path,
            "-map",
            "0:v:0",
            "-vf",
            f"trim=start={start}:end={end},setpts=PTS-STARTPTS,fps=4,scale=96:54,format=gray",
            "-f",
            "rawvideo",
            str(out_path),
        ]
    )


def extract_audio_signature(path, start, end, out_path):
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            path,
            "-map",
            "0:a:0",
            "-af",
            f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS,aresample=8000",
            "-ac",
            "1",
            "-f",
            "s16le",
            str(out_path),
        ]
    )


def frame_vector(path):
    data = np.fromfile(path, dtype=np.uint8)
    frame_size = 96 * 54
    frame_count = data.size // frame_size
    assert frame_count >= 4, f"not enough frames sampled from {path}"
    frames = data[: frame_count * frame_size].reshape(frame_count, frame_size)
    return frames.astype(np.float32).reshape(-1)


def audio_vector(path):
    data = np.fromfile(path, dtype=np.int16).astype(np.float32)
    assert data.size >= 3000, f"audio sample too short in {path}"
    trim = min(500, data.size // 12)
    if trim > 0 and data.size > 2 * trim:
        data = data[trim:-trim]
    return data


def cosine_similarity(a, b):
    length = min(len(a), len(b))
    assert length > 0
    a = a[:length] - np.mean(a[:length])
    b = b[:length] - np.mean(b[:length])
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    assert denom > 0
    return float(np.dot(a, b) / denom)


def rational_to_float(value):
    num, den = value.split("/")
    return float(num) / float(den)


def load_plan():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_expected_refs(plan, clip, video_out_path, audio_out_path):
    canvas = plan["canvas"]
    input_path = os.path.join(ROOT, clip["file"])
    source_duration = float(ffprobe_json(input_path)["format"]["duration"])
    target = float(clip["target_duration_sec"])

    video_filter = (
        f"scale={canvas['width']}:{canvas['height']}:force_original_aspect_ratio=increase,"
        f"crop={canvas['width']}:{canvas['height']},fps={canvas['frame_rate']},format=yuv420p"
    )
    audio_filter = f"aresample={canvas['audio_sample_rate_hz']}"

    if source_duration < target:
        pad = target - source_duration
        video_filter = f"{video_filter},tpad=stop_mode=clone:stop_duration={pad:.3f}"
        audio_filter = f"{audio_filter},apad=pad_dur={pad:.3f}"

    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-vf",
            f"{video_filter},trim=end={target:.3f},setpts=PTS-STARTPTS,fps=4,scale=96:54,format=gray",
            "-f",
            "rawvideo",
            str(video_out_path),
        ]
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-af",
            f"{audio_filter},atrim=end={target:.3f},asetpts=PTS-STARTPTS,aresample=8000",
            "-ac",
            "1",
            "-f",
            "s16le",
            str(audio_out_path),
        ]
    )


def media_streams(path):
    info = ffprobe_json(path)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    duration = float(info["format"]["duration"])
    return video, audio, duration


def mono_rms(path, start, end):
    pcm_path = TMP_DIR / f"tail_{abs(hash((path, start, end)))}.pcm"
    extract_audio_signature(path, start, end, pcm_path)
    data = np.fromfile(pcm_path, dtype=np.int16).astype(np.float32)
    if data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(data))))


class TestStorefrontLoop:
    @classmethod
    def setup_class(cls):
        TMP_DIR.mkdir(parents=True, exist_ok=True)

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_VIDEO), "missing /outputs/storefront_loop.mp4"

    def test_output_media_spec(self):
        plan = load_plan()
        canvas = plan["canvas"]
        video, audio, _ = media_streams(OUTPUT_VIDEO)

        assert video["codec_name"] == canvas["video_codec"]
        assert int(video["width"]) == canvas["width"]
        assert int(video["height"]) == canvas["height"]
        assert abs(rational_to_float(video["avg_frame_rate"]) - canvas["frame_rate"]) <= 0.01

        assert audio["codec_name"] == canvas["audio_codec"]
        assert int(audio["sample_rate"]) == canvas["audio_sample_rate_hz"]
        assert int(audio["channels"]) == canvas["audio_channels"]

    def test_total_duration_matches_schedule(self):
        plan = load_plan()
        _, _, duration = media_streams(OUTPUT_VIDEO)
        expected = sum(clip["target_duration_sec"] for clip in plan["clips"])
        assert abs(duration - expected) <= 0.12, (
            f"duration mismatch: got {duration:.3f}, expected {expected:.3f}"
        )

    def test_segments_match_scheduled_content(self):
        plan = load_plan()
        expected_video_refs = []
        expected_audio_refs = []

        for idx, clip in enumerate(plan["clips"]):
            video_ref = TMP_DIR / f"expected_{idx}.raw"
            audio_ref = TMP_DIR / f"expected_{idx}.pcm"
            build_expected_refs(plan, clip, video_ref, audio_ref)
            expected_video_refs.append(frame_vector(video_ref))
            expected_audio_refs.append(audio_vector(audio_ref))

        cursor = 0.0
        for idx, clip in enumerate(plan["clips"]):
            duration = clip["target_duration_sec"]
            out_video = TMP_DIR / f"actual_{idx}.raw"
            out_audio = TMP_DIR / f"actual_{idx}.pcm"

            extract_video_signature(OUTPUT_VIDEO, cursor, cursor + duration, out_video)
            extract_audio_signature(OUTPUT_VIDEO, cursor, cursor + duration, out_audio)
            actual_video = frame_vector(out_video)
            actual_audio = audio_vector(out_audio)

            video_scores = [cosine_similarity(actual_video, ref) for ref in expected_video_refs]
            audio_scores = [cosine_similarity(actual_audio, ref) for ref in expected_audio_refs]

            best_video = int(np.argmax(video_scores))
            best_audio = int(np.argmax(audio_scores))

            assert best_video == idx, f"video segment {idx} matched clip {best_video} instead"
            assert best_audio == idx, f"audio segment {idx} matched clip {best_audio} instead"
            assert video_scores[idx] >= 0.94, f"video similarity too low for clip {idx}: {video_scores[idx]:.3f}"
            assert audio_scores[idx] >= 0.90, f"audio similarity too low for clip {idx}: {audio_scores[idx]:.3f}"
            cursor += duration

    def test_padded_segments_freeze_last_frame_and_end_silently(self):
        plan = load_plan()
        cursor = 0.0

        for idx, clip in enumerate(plan["clips"]):
            input_path = os.path.join(ROOT, clip["file"])
            source_duration = float(ffprobe_json(input_path)["format"]["duration"])
            target = float(clip["target_duration_sec"])

            if source_duration < target:
                tail_start = cursor + max(target - 0.45, 0.0)
                tail_end = cursor + target

                tail_raw = TMP_DIR / f"freeze_tail_{idx}.raw"
                run(
                    [
                        "ffmpeg",
                        "-y",
                        "-loglevel",
                        "error",
                        "-i",
                        OUTPUT_VIDEO,
                        "-map",
                        "0:v:0",
                        "-vf",
                        f"trim=start={tail_start}:end={tail_end},setpts=PTS-STARTPTS,fps=8,scale=64:36,format=gray",
                        "-f",
                        "rawvideo",
                        str(tail_raw),
                    ]
                )
                data = np.fromfile(tail_raw, dtype=np.uint8)
                frame_size = 64 * 36
                frame_count = data.size // frame_size
                assert frame_count >= 3, "not enough frames to inspect frozen tail"
                frames = data[: frame_count * frame_size].reshape(frame_count, frame_size).astype(np.float32)
                diffs = np.mean(np.abs(np.diff(frames, axis=0)), axis=1)
                assert float(np.max(diffs)) <= 1.2, f"tail is not visually frozen for clip {idx}"

                tail_rms = mono_rms(OUTPUT_VIDEO, tail_start, tail_end)
                assert tail_rms <= 30.0, f"tail audio is not silent enough for clip {idx}: {tail_rms:.2f}"

            cursor += target
