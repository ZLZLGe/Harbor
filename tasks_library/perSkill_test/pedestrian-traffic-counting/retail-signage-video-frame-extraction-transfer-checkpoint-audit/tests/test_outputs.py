import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


INPUT_ROOT = Path("/app/input")
PLAN_PATH = INPUT_ROOT / "checkpoint_requests.json"
OUTPUT_ROOT = Path("/app/output")
REPORT_PATH = OUTPUT_ROOT / "checkpoint_audit_report.json"


def probe_video(video_path: Path) -> tuple[float, int]:
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), f"无法打开输入视频: {video_path}"
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return fps, total_frames


def read_source_frame(video_path: Path, frame_index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), f"无法打开输入视频: {video_path}"
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    assert ok, f"无法读取源帧 {frame_index}: {video_path}"
    return frame


def image_distance(left: np.ndarray, right: np.ndarray) -> float:
    assert left.shape == right.shape, "输出图像尺寸与源帧不一致"
    diff = np.abs(left.astype(np.int16) - right.astype(np.int16))
    return float(diff.mean())


def expected_output_file(item: dict) -> str:
    timestamp_ms = round(float(item["timestamp_seconds"]) * 1000)
    return (
        Path("checkpoint_frames")
        / item["store_code"]
        / f"{item['checkpoint_id']}__t{timestamp_ms:06d}.jpg"
    ).as_posix()


def build_expected_report() -> tuple[dict, list[dict]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    requests = []
    unreachable = []
    metadata_cache: dict[str, tuple[float, int]] = {}

    for item in plan["requests"]:
        source_video = item["source_video"]
        video_path = INPUT_ROOT / source_video
        if source_video not in metadata_cache:
            metadata_cache[source_video] = probe_video(video_path)

        fps, total_frames = metadata_cache[source_video]
        timestamp = float(item["timestamp_seconds"])
        frame_index = math.floor(timestamp * fps + 1e-9)
        captured = timestamp >= 0 and frame_index < total_frames
        output_file = expected_output_file(item) if captured else None

        if not captured:
            unreachable.append(item["checkpoint_id"])

        requests.append(
            {
                "checkpoint_id": item["checkpoint_id"],
                "store_code": item["store_code"],
                "source_video": source_video,
                "requested_timestamp_seconds": item["timestamp_seconds"],
                "status": "captured" if captured else "unreachable",
                "output_file": output_file,
                "_frame_index": frame_index,
                "_total_frames": total_frames,
            }
        )

    report = {
        "audit_id": plan["audit_id"],
        "total_requests": len(plan["requests"]),
        "captured_count": sum(1 for item in requests if item["status"] == "captured"),
        "unreachable_count": len(unreachable),
        "unreachable_checkpoints": unreachable,
    }
    return report, requests


def assert_captured_image_matches(video_path: Path, frame_index: int, image_path: Path, total_frames: int) -> None:
    assert image_path.exists(), f"缺少输出 JPG: {image_path}"

    with Image.open(image_path) as image:
        assert image.format == "JPEG", f"输出文件不是 JPG: {image_path}"

    actual = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    assert actual is not None, f"无法读取输出 JPG: {image_path}"

    start = max(0, frame_index - 2)
    end = min(total_frames - 1, frame_index + 2)
    distances = {}
    for candidate in range(start, end + 1):
        expected = read_source_frame(video_path, candidate)
        distances[candidate] = image_distance(expected, actual)

    best_index = min(distances, key=distances.get)
    assert best_index == frame_index, (
        f"{image_path} 对应的最接近源帧不是目标帧。"
        f" 目标帧: {frame_index}, 最接近帧: {best_index}, 距离表: {distances}"
    )
    assert distances[frame_index] < 6.0, (
        f"{image_path} 与目标帧差异过大，可能不是从对应时间点导出的图像。"
        f" 平均像素差: {distances[frame_index]:.3f}"
    )


def test_checkpoint_audit_report_and_jpgs():
    assert REPORT_PATH.exists(), "缺少主输出文件 /app/output/checkpoint_audit_report.json"

    actual = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    expected_report, expected_requests = build_expected_report()

    for field, value in expected_report.items():
        assert actual.get(field) == value, f"顶层字段 {field} 不符合要求"

    assert isinstance(actual.get("requests"), list), "requests 必须是数组"
    assert len(actual["requests"]) == len(expected_requests), "requests 数量与输入清单不一致"

    for actual_item, expected_item in zip(actual["requests"], expected_requests):
        for field in [
            "checkpoint_id",
            "store_code",
            "source_video",
            "requested_timestamp_seconds",
            "status",
            "output_file",
        ]:
            assert actual_item.get(field) == expected_item[field], (
                f"请求 {expected_item['checkpoint_id']} 的字段 {field} 不正确"
            )

        image_path = OUTPUT_ROOT / expected_item["output_file"] if expected_item["output_file"] else None
        if expected_item["status"] == "captured":
            video_path = INPUT_ROOT / expected_item["source_video"]
            assert_captured_image_matches(
                video_path,
                expected_item["_frame_index"],
                image_path,
                expected_item["_total_frames"],
            )
        else:
            assert image_path is None, "unreachable 请求不应有输出路径"

    referenced_files = {
        item["output_file"]
        for item in expected_requests
        if item["status"] == "captured"
    }

    for store_dir in (OUTPUT_ROOT / "checkpoint_frames").glob("*"):
        if store_dir.is_dir():
            for path in store_dir.iterdir():
                rel = path.relative_to(OUTPUT_ROOT).as_posix()
                assert rel in referenced_files, f"发现未在报告中声明的额外输出文件: {rel}"
