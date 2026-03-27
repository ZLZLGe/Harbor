import os
import re
import subprocess
import tempfile

OUTPUT = "/root/transfer1_highlight.mp4"
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
    assert os.path.exists(OUTPUT), "Missing /root/transfer1_highlight.mp4"


def test_duration_is_about_six_seconds():
    d = media_duration(OUTPUT)
    assert 5.85 <= d <= 6.15, f"Duration out of range: {d}"


def test_first_window_starts_at_source_zero():
    ssim = frame_ssim(OUTPUT, 0.0, INPUT, 0.0)
    assert ssim >= 0.93, f"Low first-window SSIM: {ssim}"


def test_second_window_jumps_to_source_nine_seconds():
    ssim = frame_ssim(OUTPUT, 3.2, INPUT, 9.2)
    assert ssim >= 0.93, f"Low second-window SSIM: {ssim}"
