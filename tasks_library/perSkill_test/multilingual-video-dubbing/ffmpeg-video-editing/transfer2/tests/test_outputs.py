import json
import os
import re
import subprocess
import tempfile

INPUT = "/root/input.mp4"
MAP_FILE = "/root/transfer2_split_map.json"
PARTS = [
    ("/root/transfer2_part_1.mp4", 0.0),
    ("/root/transfer2_part_2.mp4", 4.0),
    ("/root/transfer2_part_3.mp4", 8.0),
]


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


def test_outputs_exist():
    assert os.path.exists(MAP_FILE), "Missing split map json"
    for part, _ in PARTS:
        assert os.path.exists(part), f"Missing segment file: {part}"


def test_json_schema_and_values():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("input_file") == INPUT
    parts = data.get("parts")
    assert isinstance(parts, list) and len(parts) == 3

    for idx, expected in enumerate(PARTS):
        expected_file, expected_start = expected
        row = parts[idx]
        assert row.get("file") == expected_file
        assert abs(float(row.get("start_sec")) - expected_start) <= 0.001
        assert 3.90 <= float(row.get("duration_sec")) <= 4.10


def test_segment_boundaries_match_source():
    for part, start in PARTS:
        ssim = frame_ssim(part, 0.0, INPUT, start)
        assert ssim >= 0.93, f"Low SSIM for {part}: {ssim}"


def test_json_duration_matches_actual_files():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for row in data["parts"]:
        actual = media_duration(row["file"])
        stated = float(row["duration_sec"])
        assert abs(actual - stated) <= 0.05, f"Duration mismatch for {row['file']}"
