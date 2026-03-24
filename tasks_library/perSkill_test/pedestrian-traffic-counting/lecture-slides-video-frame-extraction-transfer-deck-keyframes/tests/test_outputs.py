import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path("/app/lectures")
VIDEO_FILE = ROOT / "recordings" / "lecture-recording.mp4"
OUTPUT_JSON = ROOT / "slide_keyframes.json"
REWARD_FILE = Path("/logs/verifier/reward.txt")


def _write_reward(value: float) -> None:
    REWARD_FILE.write_text(f"{value:.6f}\n", encoding="utf-8")


def _extract_reference_frames(temp_dir: Path) -> list[Path]:
    pattern = temp_dir / "slide_%03d.jpg"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-skip_frame",
            "nokey",
            "-i",
            str(VIDEO_FILE),
            "-vsync",
            "vfr",
            str(pattern),
        ],
        check=True,
    )
    return sorted(temp_dir.glob("slide_*.jpg"))


def _ssim_score(actual_path: Path, expected_path: Path) -> float:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(actual_path),
            "-i",
            str(expected_path),
            "-lavfi",
            "ssim",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    marker = "All:"
    for line in result.stderr.splitlines():
        if marker in line:
            tail = line.split(marker, 1)[1]
            value = tail.split()[0]
            return float(value)
    raise AssertionError(f"Unable to parse SSIM output for {actual_path.name}")


def _load_actual_manifest() -> list[dict[str, object]]:
    assert OUTPUT_JSON.is_file(), "slide_keyframes.json not found at /app/lectures"
    content = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    assert isinstance(content, list), "slide_keyframes.json must contain a JSON array"
    return content


def _build_expected_manifest(reference_frames: list[Path]) -> list[dict[str, object]]:
    expected = []
    for index, frame_path in enumerate(reference_frames, start=1):
        expected.append(
            {
                "video_filename": VIDEO_FILE.name,
                "sequence_number": index,
                "frame_filename": f"keyframes/{VIDEO_FILE.stem}/{frame_path.name}",
            }
        )
    return expected


def _json_row_reward(actual: dict[str, object], expected: dict[str, object]) -> float:
    reward = 0.0
    if actual.get("video_filename") == expected["video_filename"]:
        reward += 0.2
    if actual.get("sequence_number") == expected["sequence_number"]:
        reward += 0.3
    if actual.get("frame_filename") == expected["frame_filename"]:
        reward += 0.5
    return reward


def test_outputs() -> None:
    if not OUTPUT_JSON.exists():
        _write_reward(0.0)
        raise AssertionError("slide_keyframes.json not found at /app/lectures")

    try:
        actual_manifest = _load_actual_manifest()

        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            reference_frames = _extract_reference_frames(temp_dir)
            expected_manifest = _build_expected_manifest(reference_frames)

            print("\nActual manifest:")
            for row in actual_manifest:
                print(row)

            assert len(actual_manifest) == len(expected_manifest), (
                f"Expected {len(expected_manifest)} manifest rows, got {len(actual_manifest)}"
            )

            total_reward = 0.0
            for actual_row, expected_row, reference_frame in zip(actual_manifest, expected_manifest, reference_frames):
                assert isinstance(actual_row, dict), f"Each manifest row must be an object, got {type(actual_row)}"
                assert set(actual_row.keys()) == {
                    "video_filename",
                    "sequence_number",
                    "frame_filename",
                }, f"Unexpected keys in row: {actual_row}"

                total_reward += _json_row_reward(actual_row, expected_row)

                actual_frame = ROOT / str(actual_row["frame_filename"])
                if actual_frame.exists():
                    similarity = _ssim_score(actual_frame, reference_frame)
                else:
                    similarity = 0.0
                print(
                    f"sequence={expected_row['sequence_number']} "
                    f"json_reward={_json_row_reward(actual_row, expected_row):.4f} "
                    f"ssim={similarity:.6f}"
                )
                total_reward += similarity

            average_reward = total_reward / (2 * len(expected_manifest))
            _write_reward(average_reward)

            assert actual_manifest == expected_manifest, (
                "Manifest content mismatch.\n"
                f"Actual:   {actual_manifest}\n"
                f"Expected: {expected_manifest}"
            )

            for actual_row, reference_frame in zip(actual_manifest, reference_frames):
                actual_frame = ROOT / str(actual_row["frame_filename"])
                assert actual_frame.is_file(), f"Missing output frame: {actual_frame}"
                similarity = _ssim_score(actual_frame, reference_frame)
                assert similarity >= 0.999, (
                    f"Representative frame does not match reference slide closely enough: "
                    f"{actual_frame.name} vs {reference_frame.name}, SSIM={similarity:.6f}"
                )
    except Exception:
        if not REWARD_FILE.exists():
            _write_reward(0.0)
        raise
