import csv
from pathlib import Path

import cv2
import numpy as np


INPUT_ROOT = Path("/app/input")
VIDEOS_ROOT = INPUT_ROOT / "videos"
CONFIG_PATH = INPUT_ROOT / "replay_ranges.csv"
OUTPUT_ROOT = Path("/app/output")
SUMMARY_PATH = OUTPUT_ROOT / "replay_range_summary.csv"


def load_clip_config() -> list[dict[str, str]]:
    with CONFIG_PATH.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_summary_rows() -> list[dict[str, str]]:
    with SUMMARY_PATH.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == [
            "clip_id",
            "source_video",
            "start_frame",
            "end_frame",
            "frames_written",
            "output_dir",
        ], "汇总 CSV 表头不符合要求"
        return list(reader)


def read_source_frame(video_path: Path, frame_index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), f"无法打开输入视频: {video_path}"
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    assert ok, f"无法读取源视频帧 {frame_index}: {video_path}"
    return frame


def test_summary_and_png_ranges():
    assert SUMMARY_PATH.exists(), "缺少主输出文件 /app/output/replay_range_summary.csv"

    clips = load_clip_config()
    summary_rows = read_summary_rows()

    assert len(summary_rows) == len(clips), "汇总 CSV 数据行数与输入配置不一致"

    for clip, row in zip(clips, summary_rows):
        clip_id = clip["clip_id"]
        source_video = clip["source_video"]
        start_frame = int(clip["start_frame"])
        end_frame = int(clip["end_frame"])
        expected_count = end_frame - start_frame + 1
        expected_output_dir = f"replay_batches/{clip_id}"

        assert row == {
            "clip_id": clip_id,
            "source_video": source_video,
            "start_frame": str(start_frame),
            "end_frame": str(end_frame),
            "frames_written": str(expected_count),
            "output_dir": expected_output_dir,
        }, f"汇总 CSV 中片段 {clip_id} 的行内容不正确"

        clip_dir = OUTPUT_ROOT / expected_output_dir
        assert clip_dir.is_dir(), f"缺少片段目录: {clip_dir}"

        actual_files = sorted(path.name for path in clip_dir.iterdir() if path.is_file())
        expected_files = [
            f"frame_{frame_index:06d}.png"
            for frame_index in range(start_frame, end_frame + 1)
        ]
        assert actual_files == expected_files, f"片段 {clip_id} 的 PNG 文件集合不正确"

        video_path = VIDEOS_ROOT / source_video
        for frame_index, filename in zip(range(start_frame, end_frame + 1), expected_files):
            source_frame = read_source_frame(video_path, frame_index)
            output_frame = cv2.imread(str(clip_dir / filename), cv2.IMREAD_COLOR)
            assert output_frame is not None, f"无法读取输出 PNG: {clip_dir / filename}"
            assert output_frame.shape == source_frame.shape, f"片段 {clip_id} 的帧尺寸不匹配"
            assert np.array_equal(output_frame, source_frame), (
                f"片段 {clip_id} 的输出帧 {filename} 与源视频帧 {frame_index} 不一致"
            )
