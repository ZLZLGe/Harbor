import os
import re
import subprocess
import tempfile

OUTPUT = "/root/transfer3_gap_removed.mp4"
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
    assert os.path.exists(OUTPUT), "Missing /root/transfer3_gap_removed.mp4"


def test_duration_removed_two_seconds():
    in_d = media_duration(INPUT)
    out_d = media_duration(OUTPUT)
    assert abs(out_d - (in_d - 2.0)) <= 0.20, f"Expected ~{in_d - 2.0}, got {out_d}"


def test_front_part_is_preserved():
    ssim = frame_ssim(OUTPUT, 0.5, INPUT, 0.5)
    assert ssim >= 0.93, f"Low front-part SSIM: {ssim}"


def test_cut_boundary_jumps_from_around_4s_to_around_6s():
    ssim_a = frame_ssim(OUTPUT, 4.2, INPUT, 6.2)
    ssim_b = frame_ssim(OUTPUT, 8.0, INPUT, 10.0)
    assert ssim_a >= 0.93, f"Low boundary SSIM A: {ssim_a}"
    assert ssim_b >= 0.93, f"Low boundary SSIM B: {ssim_b}"
