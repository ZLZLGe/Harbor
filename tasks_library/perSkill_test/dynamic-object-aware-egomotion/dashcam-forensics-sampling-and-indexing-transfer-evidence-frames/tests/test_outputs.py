import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path("/root")
VIDEO_PATH = ROOT / "dashcam_clip.mp4"
MANIFEST_PATH = ROOT / "evidence_manifest.json"
EVENTS_PATH = ROOT / "incident_times.json"
OUTPUT_JSON = ROOT / "evidence_index.json"
OUTPUT_DIR = ROOT / "evidence_frames"


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_events() -> list[dict]:
    with EVENTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def sample_record(sample_index: int, manifest: dict) -> dict:
    frame_id = int(manifest["sample_offset_frame"]) + sample_index * int(manifest["sample_stride_frames"])
    sample_timestamp_ms = int(round(frame_id * 1000.0 / float(manifest["video_fps"])))
    return {
        "sample_index": sample_index,
        "frame_id": frame_id,
        "sample_timestamp_ms": sample_timestamp_ms,
        "jpeg_path": f"/root/evidence_frames/sample_{sample_index}.jpg",
    }


def choose_nearest_sample(event_time_ms: int, manifest: dict) -> dict:
    best = None
    for sample_index in range(int(manifest["sample_count"])):
        record = sample_record(sample_index, manifest)
        candidate = (abs(int(event_time_ms) - record["sample_timestamp_ms"]), sample_index, record)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2]


def expected_output() -> dict:
    manifest = load_manifest()
    events = load_events()
    projected = []
    for event in events:
        selected = choose_nearest_sample(int(event["event_time_ms"]), manifest)
        projected.append(
            {
                "event_id": event["event_id"],
                "event_time_ms": int(event["event_time_ms"]),
                "sample_index": selected["sample_index"],
                "frame_id": selected["frame_id"],
                "sample_timestamp_ms": selected["sample_timestamp_ms"],
                "jpeg_path": selected["jpeg_path"],
            }
        )
    return {
        "sampling": {
            "video_fps": manifest["video_fps"],
            "sample_offset_frame": manifest["sample_offset_frame"],
            "sample_stride_frames": manifest["sample_stride_frames"],
            "sample_count": manifest["sample_count"],
        },
        "events": projected,
    }


def extract_reference_frame(frame_id: int, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(VIDEO_PATH),
            "-vf",
            f"select=eq(n\\,{frame_id})",
            "-frames:v",
            "1",
            str(output_path),
        ],
        check=True,
    )


def test_output_files_exist():
    assert OUTPUT_JSON.exists(), "Missing /root/evidence_index.json"
    assert OUTPUT_DIR.exists(), "Missing /root/evidence_frames"


def test_json_schema_and_values_match_expected_projection():
    with OUTPUT_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "evidence_index.json must be a JSON object"
    assert set(data.keys()) == {"sampling", "events"}, "top-level keys must be exactly sampling and events"
    assert data == expected_output()


def test_unique_jpeg_set_matches_selected_samples():
    expected = expected_output()
    expected_names = {
        Path(item["jpeg_path"]).name
        for item in expected["events"]
    }
    actual_names = {path.name for path in OUTPUT_DIR.glob("*.jpg")}

    assert actual_names == expected_names, "JPEG set must match the distinct selected sample indices"


def test_exported_jpegs_match_declared_video_frames():
    expected = expected_output()
    checked = set()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        for item in expected["events"]:
            jpeg_path = Path(item["jpeg_path"])
            if jpeg_path in checked:
                continue
            checked.add(jpeg_path)

            assert jpeg_path.exists(), f"Missing declared JPEG: {jpeg_path}"

            reference_png = tmp_dir_path / f"frame_{item['sample_index']}.png"
            extract_reference_frame(int(item["frame_id"]), reference_png)

            actual = np.array(Image.open(jpeg_path).convert("RGB"), dtype=np.int16)
            reference = np.array(Image.open(reference_png).convert("RGB"), dtype=np.int16)

            assert actual.shape == reference.shape, "exported JPEG resolution does not match source frame"

            abs_diff = np.abs(actual - reference)
            mean_abs_diff = float(abs_diff.mean())
            p99_abs_diff = float(np.percentile(abs_diff, 99))

            assert mean_abs_diff <= 6.0, f"JPEG differs too much from source frame: mean_abs_diff={mean_abs_diff:.2f}"
            assert p99_abs_diff <= 60.0, f"JPEG differs too much from source frame tail pixels: p99_abs_diff={p99_abs_diff:.2f}"
