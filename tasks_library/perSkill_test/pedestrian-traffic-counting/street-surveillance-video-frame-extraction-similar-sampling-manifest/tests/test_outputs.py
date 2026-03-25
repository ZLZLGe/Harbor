import json
import math
from pathlib import Path

import cv2
from PIL import Image


INPUT_ROOT = Path("/app/input")
FEEDS_ROOT = INPUT_ROOT / "feeds"
OUTPUT_ROOT = Path("/app/output")
MANIFEST_PATH = OUTPUT_ROOT / "surveillance_sampling_manifest.json"
INTERVAL_SECONDS = 2.0


def probe_video(video_path: Path) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), f"无法打开输入视频: {video_path}"

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    duration = frame_count / fps
    timestamps = []
    current = 0.0
    while current < duration - 1e-9:
        timestamps.append(current)
        current += INTERVAL_SECONDS

    return {
        "source_file": video_path.relative_to(INPUT_ROOT).as_posix(),
        "fps": fps,
        "timestamps": timestamps,
        "size": (width, height),
        "frames_dir": (Path("review_frames") / video_path.relative_to(FEEDS_ROOT).with_suffix("")).as_posix(),
    }


def assert_json_number(value, field_name: str) -> None:
    assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{field_name} 必须是 JSON 数值"


def assert_close(actual: float, expected: float, field_name: str, abs_tol: float = 1e-3) -> None:
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=abs_tol), (
        f"{field_name} 不正确: 期望接近 {expected}, 实际为 {actual}"
    )


def test_manifest_and_frames():
    assert MANIFEST_PATH.exists(), "缺少主输出文件 /app/output/surveillance_sampling_manifest.json"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    input_videos = sorted(FEEDS_ROOT.rglob("*.mp4"))
    expected = [probe_video(path) for path in input_videos]

    assert manifest.get("sampling_interval_seconds") == 2
    assert manifest.get("video_count") == len(expected)
    assert isinstance(manifest.get("videos"), list)
    assert len(manifest["videos"]) == len(expected)
    assert manifest.get("total_extracted_frames") == sum(len(item["timestamps"]) for item in expected)

    actual_sources = [item.get("source_file") for item in manifest["videos"]]
    expected_sources = [item["source_file"] for item in expected]
    assert actual_sources == expected_sources
    assert len({item["frames_dir"] for item in expected}) == len(expected), "每个视频都必须映射到独立 frames_dir"

    for actual, exp in zip(manifest["videos"], expected):
        assert actual.get("source_file") == exp["source_file"]
        assert_json_number(actual.get("fps"), f"{exp['source_file']} 的 fps")
        assert_close(float(actual["fps"]), exp["fps"], f"{exp['source_file']} 的 fps")
        assert actual.get("frames_dir") == exp["frames_dir"]
        assert actual.get("extracted_count") == len(exp["timestamps"])
        assert isinstance(actual.get("samples"), list)
        assert len(actual["samples"]) == len(exp["timestamps"])

        frames_dir_path = OUTPUT_ROOT / actual["frames_dir"]
        assert frames_dir_path.is_dir(), f"frames_dir 不存在或不是目录: {frames_dir_path}"

        for index, (sample, timestamp) in enumerate(zip(actual["samples"], exp["timestamps"])):
            expected_rel = f"{exp['frames_dir']}/frame_{index:04d}.jpg"
            assert_json_number(sample.get("timestamp_seconds"), f"{expected_rel} 的 timestamp_seconds")
            assert_close(
                float(sample["timestamp_seconds"]),
                timestamp,
                f"{expected_rel} 的 timestamp_seconds",
                abs_tol=1e-9,
            )
            assert sample.get("relative_path") == expected_rel
            assert Path(sample["relative_path"]).parent.as_posix() == actual["frames_dir"]

            image_path = OUTPUT_ROOT / sample["relative_path"]
            assert image_path.exists(), f"缺少抽出的 JPEG: {image_path}"

            with Image.open(image_path) as image:
                assert image.format == "JPEG"
                assert image.size == exp["size"]
