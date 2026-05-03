from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


INPUT_DIR = Path(os.environ.get("MEDIA_PICK_INPUT_DIR", "/root/media_pick/input"))
OUTPUT_DIR = Path(os.environ.get("MEDIA_PICK_OUTPUT_DIR", "/root/media_pick/output"))
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")


def load_manifest() -> dict:
    return json.loads((INPUT_DIR / "clip_manifest.json").read_text(encoding="utf-8"))


def load_layout() -> dict:
    return json.loads((INPUT_DIR / "layout_spec.json").read_text(encoding="utf-8"))


def load_requests() -> list[dict[str, str]]:
    with (INPUT_DIR / "shot_requests.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def clips_by_id() -> dict[str, dict]:
    return {clip["clip_id"]: clip for clip in load_manifest()["clips"]}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def parse_video_info(path: Path) -> dict[str, float]:
    proc = subprocess.run(
        [FFMPEG_BIN, "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    text = proc.stderr
    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", text)
    video_match = re.search(r"Video: .*?, (\d+)x(\d+).*?, ([0-9.]+) fps", text)
    assert duration_match, f"Could not parse duration for {path}"
    assert video_match, f"Could not parse video stream for {path}"
    hours, minutes, seconds = duration_match.groups()
    width, height, fps = video_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return {
        "duration_sec": duration,
        "width": int(width),
        "height": int(height),
        "fps": float(fps),
    }


def image_array(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img.convert("RGB"), dtype=np.int16)


def mean_abs_diff(left: np.ndarray, right: np.ndarray) -> float:
    assert left.shape == right.shape, f"Shape mismatch: {left.shape} vs {right.shape}"
    return float(np.mean(np.abs(left - right)))


def expected_frame(video_path: Path, request: dict[str, str]) -> np.ndarray:
    locator = request["still_locator"].strip()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "oracle.png"
        if locator.startswith("--time "):
            run([
                FFMPEG_BIN,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                locator.removeprefix("--time ").strip(),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(out),
            ])
        elif locator.startswith("--index "):
            run([
                FFMPEG_BIN,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"select=eq(n\\,{locator.removeprefix('--index ').strip()})",
                "-vframes",
                "1",
                str(out),
            ])
        else:
            run([
                FFMPEG_BIN,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "select=eq(n\\,0)",
                "-vframes",
                "1",
                str(out),
            ])
        return image_array(out)


def frame_from_video(video_path: Path, timestamp_sec: float) -> np.ndarray:
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "sample.png"
        run([
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp_sec:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(out),
        ])
        return image_array(out)


def grouped_requests() -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in load_requests():
        groups[row["clip_id"]].append(row)
    return groups


def actual_top_level_paths() -> set[str]:
    return {path.name for path in OUTPUT_DIR.iterdir()}


def test_output_files_exist_and_basic_schema() -> None:
    assert OUTPUT_DIR.exists(), "Missing /root/media_pick/output"
    assert actual_top_level_paths() == {"stills", "previews", "sheets", "frame_index.json", "delivery_report.json"}

    frame_index = json.loads((OUTPUT_DIR / "frame_index.json").read_text(encoding="utf-8"))
    delivery = json.loads((OUTPUT_DIR / "delivery_report.json").read_text(encoding="utf-8"))

    assert isinstance(frame_index.get("clips"), list) and frame_index["clips"], "frame_index.json must list clips"
    assert isinstance(delivery.get("videos_processed"), list) and delivery["videos_processed"], "delivery_report.json must list clips"
    assert isinstance(delivery.get("issues"), list)
    assert isinstance(delivery.get("notes"), list)


def test_stills_cover_all_requests_and_match_requested_frames() -> None:
    manifest = clips_by_id()
    requests = load_requests()
    expected_ids = {row["request_id"] for row in requests}
    still_dir = OUTPUT_DIR / "stills"
    actual_ids = {path.stem for path in still_dir.glob("*.png")}
    assert actual_ids == expected_ids, "stills/ must cover every request exactly once"

    frame_index = json.loads((OUTPUT_DIR / "frame_index.json").read_text(encoding="utf-8"))
    indexed = {
        req["request_id"]: req
        for clip in frame_index["clips"]
        for req in clip.get("requests", [])
    }
    assert set(indexed) == expected_ids, "frame_index.json must cover every request exactly once"

    for row in requests:
        clip = manifest[row["clip_id"]]
        video_path = INPUT_DIR / "videos" / clip["filename"]
        still_path = still_dir / f"{row['request_id']}.png"
        assert still_path.exists(), f"Missing still {still_path.name}"
        actual = image_array(still_path)
        oracle = expected_frame(video_path, row)
        assert actual.shape == oracle.shape
        assert actual.shape[1] == clip["width"]
        assert actual.shape[0] == clip["height"]
        assert mean_abs_diff(actual, oracle) <= 0.2, f"{row['request_id']} does not match the requested frame"

        entry = indexed[row["request_id"]]
        assert entry["still_locator"] == row["still_locator"]
        assert entry["still_path"] == f"stills/{row['request_id']}.png"
        assert entry["preview_path"] == f"previews/{row['request_id']}.mp4"
        assert int(entry["width"]) == clip["width"]
        assert int(entry["height"]) == clip["height"]
        digest = hashlib.sha256(still_path.read_bytes()).hexdigest()
        assert entry["sha256"] == digest


def test_previews_align_with_source_windows() -> None:
    manifest = clips_by_id()
    for row in load_requests():
        clip = manifest[row["clip_id"]]
        source_video = INPUT_DIR / "videos" / clip["filename"]
        preview_path = OUTPUT_DIR / "previews" / f"{row['request_id']}.mp4"
        assert preview_path.exists(), f"Missing preview {preview_path.name}"

        info = parse_video_info(preview_path)
        assert abs(info["duration_sec"] - float(row["preview_duration_sec"])) <= 0.25
        assert info["width"] == clip["width"]
        assert info["height"] == clip["height"]

        duration = info["duration_sec"]
        sample_points = sorted({0.0, min(0.75, max(duration / 3.0, 0.0)), max(duration - 0.20, 0.0)})
        for sample in sample_points:
            actual = frame_from_video(preview_path, sample)
            expected = frame_from_video(source_video, float(row["preview_start_sec"]) + sample)
            assert actual.shape == expected.shape
            assert mean_abs_diff(actual, expected) <= 6.5, f"{row['request_id']} preview drifts from source content"


def test_contact_sheets_match_layout_and_cell_content() -> None:
    manifest = clips_by_id()
    layout = load_layout()
    requests_by_clip = grouped_requests()

    assert layout["grid_columns"] == 2
    assert layout["grid_rows_per_clip"] == 2
    assert layout["cell_gap_px"] == 0

    for clip_id, requests in requests_by_clip.items():
        clip = manifest[clip_id]
        sheet_path = OUTPUT_DIR / "sheets" / f"{clip_id}_sheet.jpg"
        assert sheet_path.exists(), f"Missing sheet for {clip_id}"
        with Image.open(sheet_path) as sheet:
            sheet_rgb = np.array(sheet.convert("RGB"), dtype=np.int16)
            assert sheet.width == clip["width"] * 2
            assert sheet.height == clip["height"] * 2

            for idx, row in enumerate(requests):
                col = idx % 2
                row_idx = idx // 2
                left = col * clip["width"]
                top = row_idx * clip["height"]
                cell = sheet_rgb[top : top + clip["height"], left : left + clip["width"], :]
                still = image_array(OUTPUT_DIR / "stills" / f"{row['request_id']}.png")
                assert cell.shape == still.shape
                assert mean_abs_diff(cell, still) <= 8.5, f"{clip_id} sheet cell {idx} does not match still {row['request_id']}"


def test_metadata_reports_match_generated_files() -> None:
    manifest = clips_by_id()
    requests = load_requests()
    requests_by_clip = grouped_requests()
    frame_index = json.loads((OUTPUT_DIR / "frame_index.json").read_text(encoding="utf-8"))
    delivery = json.loads((OUTPUT_DIR / "delivery_report.json").read_text(encoding="utf-8"))

    clips = frame_index.get("clips", [])
    assert [clip["clip_id"] for clip in clips] == [clip["clip_id"] for clip in load_manifest()["clips"]]

    for clip_entry in clips:
        clip_id = clip_entry["clip_id"]
        clip = manifest[clip_id]
        assert clip_entry["source_video"] in {clip["filename"], f"videos/{clip['filename']}"}
        assert clip_entry["sheet_path"] == f"sheets/{clip_id}_sheet.jpg"
        assert [row["request_id"] for row in clip_entry["requests"]] == [row["request_id"] for row in requests_by_clip[clip_id]]

    expected_files = {
        "frame_index.json",
        "delivery_report.json",
        *(f"stills/{row['request_id']}.png" for row in requests),
        *(f"previews/{row['request_id']}.mp4" for row in requests),
        *(f"sheets/{clip_id}_sheet.jpg" for clip_id in requests_by_clip),
    }
    assert set(delivery["files_created"]) == expected_files

    videos_processed = delivery["videos_processed"]
    assert [entry["clip_id"] for entry in videos_processed] == [clip["clip_id"] for clip in load_manifest()["clips"]]
    for entry in videos_processed:
        clip_id = entry["clip_id"]
        clip = manifest[clip_id]
        assert entry["source_video"] in {clip["filename"], f"videos/{clip['filename']}"}
        assert entry["request_count"] == len(requests_by_clip[clip_id])
        assert entry["sheet_path"] == f"sheets/{clip_id}_sheet.jpg"
        assert entry["status"] == "pass"

    assert int(delivery["requests_processed"]) == len(requests)
    assert int(delivery["sheet_count"]) == len(requests_by_clip)
