import json
import subprocess
from pathlib import Path

INPUT_VIDEO = "/root/input.mp4"
OUTPUT_VIDEO = "/outputs/similar_preview.mp4"
EXPECTED_VIDEO = "/tmp/expected_similar_preview.mp4"


def ffprobe_json(path: str) -> dict:
    res = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        text=True,
    )
    return json.loads(res)


def video_md5_at(path: str, sec: float) -> str:
    res = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{sec}",
            "-i",
            path,
            "-frames:v",
            "1",
            "-f",
            "md5",
            "-",
        ],
        text=True,
    ).strip()
    return res


def build_expected() -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            INPUT_VIDEO,
            "-vf",
            "scale=640:360:flags=lanczos,eq=brightness=0.04:contrast=1.08,boxblur=1:1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "1",
            EXPECTED_VIDEO,
        ]
    )


def test_output_exists() -> None:
    assert Path(OUTPUT_VIDEO).exists(), f"Missing output: {OUTPUT_VIDEO}"


def test_stream_contract() -> None:
    meta = ffprobe_json(OUTPUT_VIDEO)
    v_streams = [s for s in meta["streams"] if s.get("codec_type") == "video"]
    a_streams = [s for s in meta["streams"] if s.get("codec_type") == "audio"]

    assert len(v_streams) == 1, "Output must contain exactly one video stream"
    assert len(a_streams) == 1, "Output must contain exactly one audio stream"

    v = v_streams[0]
    a = a_streams[0]

    assert int(v["width"]) == 640, f"Unexpected width: {v['width']}"
    assert int(v["height"]) == 360, f"Unexpected height: {v['height']}"
    assert v.get("pix_fmt") == "yuv420p", f"Unexpected pixel format: {v.get('pix_fmt')}"

    assert a.get("codec_name") == "aac", f"Unexpected audio codec: {a.get('codec_name')}"
    assert int(a["sample_rate"]) == 48000, f"Unexpected sample rate: {a['sample_rate']}"
    assert int(a["channels"]) == 1, f"Unexpected channel count: {a['channels']}"


def test_expected_transform_signature() -> None:
    build_expected()
    out_meta = ffprobe_json(OUTPUT_VIDEO)
    exp_meta = ffprobe_json(EXPECTED_VIDEO)

    out_duration = float(out_meta["format"]["duration"])
    exp_duration = float(exp_meta["format"]["duration"])
    assert abs(out_duration - exp_duration) <= 0.03, (
        f"Duration mismatch: output={out_duration:.4f}, expected={exp_duration:.4f}"
    )

    out_hash = video_md5_at(OUTPUT_VIDEO, 1.2)
    exp_hash = video_md5_at(EXPECTED_VIDEO, 1.2)
    assert out_hash == exp_hash, f"Frame signature mismatch: {out_hash} != {exp_hash}"


if __name__ == "__main__":
    test_output_exists()
    test_stream_contract()
    test_expected_transform_signature()
