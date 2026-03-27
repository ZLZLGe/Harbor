import os
import re
import subprocess
import tempfile

OUTPUT = "/root/similar_window.mp4"
INPUT = "/root/input.mp4"


def media_duration(path: str) -> float:
    res = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True)
    text = res.stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+))", text)
    if not m:
        raise AssertionError(f"Cannot parse duration from ffmpeg output for {path}")
    hh, mm, ss = m.groups()
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def frame_ssim(path_a: str, ts_a: float, path_b: str, ts_b: float) -> float:
    with tempfile.TemporaryDirectory() as td:
        a_png = os.path.join(td, "a.png")
        b_png = os.path.join(td, "b.png")
        subprocess.check_call([
            "ffmpeg", "-v", "error", "-y", "-ss", f"{ts_a:.3f}", "-i", path_a,
            "-frames:v", "1", a_png,
        ])
        subprocess.check_call([
            "ffmpeg", "-v", "error", "-y", "-ss", f"{ts_b:.3f}", "-i", path_b,
            "-frames:v", "1", b_png,
        ])
        res = subprocess.run(
            ["ffmpeg", "-i", a_png, "-i", b_png, "-lavfi", "ssim", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        m = re.search(r"All:([0-9.]+)", res.stderr)
        if not m:
            raise AssertionError("Cannot parse SSIM output")
        return float(m.group(1))


def test_output_exists():
    assert os.path.exists(OUTPUT), "Missing /root/similar_window.mp4"


def test_duration_is_five_seconds():
    d = media_duration(OUTPUT)
    assert 4.90 <= d <= 5.10, f"Duration out of range: {d}"


def test_start_and_end_frames_match_source_window():
    start_ssim = frame_ssim(OUTPUT, 0.0, INPUT, 2.0)
    assert start_ssim >= 0.93, f"Low start-frame SSIM: {start_ssim}"

    end_ssim = frame_ssim(OUTPUT, 4.8, INPUT, 6.8)
    assert end_ssim >= 0.93, f"Low end-frame SSIM: {end_ssim}"
