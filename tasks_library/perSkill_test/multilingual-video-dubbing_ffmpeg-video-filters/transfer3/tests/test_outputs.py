import json
import subprocess
from pathlib import Path

INPUT_VIDEO = "/root/input.mp4"
OUTPUT_VIDEO = "/outputs/transfer3_watermark_master.mp4"
EXPECTED_VIDEO = "/tmp/expected_transfer3_watermark_master.mp4"


def ffprobe_json(path: str) -> dict:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        text=True,
    )
    return json.loads(raw)


def video_md5_at(path: str, sec: float) -> str:
    return subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(sec),
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
            "scale=960:540:flags=lanczos,drawbox=x=iw-220:y=ih-90:w=200:h=70:color=black@0.35:t=fill,drawbox=x=iw-210:y=ih-80:w=180:h=50:color=yellow@0.60:t=fill,gblur=sigma=0.35",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
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


def test_stream_constraints() -> None:
    meta = ffprobe_json(OUTPUT_VIDEO)
    v = [s for s in meta["streams"] if s.get("codec_type") == "video"]
    a = [s for s in meta["streams"] if s.get("codec_type") == "audio"]

    assert len(v) == 1, "Expected one video stream"
    assert len(a) == 1, "Expected one audio stream"

    assert int(v[0]["width"]) == 960, f"Unexpected width: {v[0]['width']}"
    assert int(v[0]["height"]) == 540, f"Unexpected height: {v[0]['height']}"
    assert v[0].get("pix_fmt") == "yuv420p", f"Unexpected pixel format: {v[0].get('pix_fmt')}"

    assert a[0].get("codec_name") == "aac", f"Unexpected audio codec: {a[0].get('codec_name')}"
    assert int(a[0]["sample_rate"]) == 48000, f"Unexpected sample rate: {a[0]['sample_rate']}"
    assert int(a[0]["channels"]) == 1, f"Unexpected channel count: {a[0]['channels']}"


def test_expected_signature() -> None:
    build_expected()
    out = ffprobe_json(OUTPUT_VIDEO)
    exp = ffprobe_json(EXPECTED_VIDEO)

    out_duration = float(out["format"]["duration"])
    exp_duration = float(exp["format"]["duration"])
    assert abs(out_duration - exp_duration) <= 0.03, (
        f"Duration mismatch: output={out_duration:.4f}, expected={exp_duration:.4f}"
    )

    out_hash = video_md5_at(OUTPUT_VIDEO, 2.0)
    exp_hash = video_md5_at(EXPECTED_VIDEO, 2.0)
    assert out_hash == exp_hash, f"Frame signature mismatch: {out_hash} != {exp_hash}"


if __name__ == "__main__":
    test_output_exists()
    test_stream_constraints()
    test_expected_signature()
