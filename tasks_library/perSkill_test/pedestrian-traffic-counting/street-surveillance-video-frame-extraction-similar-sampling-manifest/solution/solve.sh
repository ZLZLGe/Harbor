#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

import cv2

INPUT_ROOT = Path("/app/input")
FEEDS_ROOT = INPUT_ROOT / "feeds"
OUTPUT_ROOT = Path("/app/output")
FRAMES_ROOT = OUTPUT_ROOT / "review_frames"
MANIFEST_PATH = OUTPUT_ROOT / "surveillance_sampling_manifest.json"
INTERVAL_SECONDS = 2.0


def build_timestamps(frame_count: int, fps: float) -> list[float]:
    duration = frame_count / fps
    timestamps = []
    current = 0.0
    while current < duration - 1e-9:
        timestamps.append(round(current, 3))
        current += INTERVAL_SECONDS
    return timestamps


def extract_video(video_path: Path) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    timestamps = build_timestamps(frame_count, fps)

    video_rel_to_feeds = video_path.relative_to(FEEDS_ROOT)
    frames_dir_rel = Path("review_frames") / video_rel_to_feeds.with_suffix("")
    frames_dir_abs = OUTPUT_ROOT / frames_dir_rel
    frames_dir_abs.mkdir(parents=True, exist_ok=True)

    samples = []
    for index, timestamp in enumerate(timestamps):
        target_frame = min(int(round(timestamp * fps)), max(frame_count - 1, 0))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"cannot read frame at {timestamp}s from {video_path}")

        relative_path = frames_dir_rel / f"frame_{index:04d}.jpg"
        absolute_path = OUTPUT_ROOT / relative_path
        if not cv2.imwrite(str(absolute_path), frame):
            raise RuntimeError(f"cannot write frame to {absolute_path}")

        samples.append(
            {
                "timestamp_seconds": timestamp,
                "relative_path": relative_path.as_posix(),
            }
        )

    cap.release()

    return {
        "source_file": video_path.relative_to(INPUT_ROOT).as_posix(),
        "fps": round(fps, 3),
        "frames_dir": frames_dir_rel.as_posix(),
        "extracted_count": len(samples),
        "samples": samples,
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    FRAMES_ROOT.mkdir(parents=True, exist_ok=True)

    video_paths = sorted(FEEDS_ROOT.rglob("*.mp4"))
    videos = [extract_video(path) for path in video_paths]
    manifest = {
        "sampling_interval_seconds": 2,
        "video_count": len(videos),
        "total_extracted_frames": sum(item["extracted_count"] for item in videos),
        "videos": videos,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
