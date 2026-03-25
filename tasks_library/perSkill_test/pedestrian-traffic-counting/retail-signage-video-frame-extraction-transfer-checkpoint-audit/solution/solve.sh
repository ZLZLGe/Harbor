#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import math
from pathlib import Path

import cv2


INPUT_PATH = Path("/app/input/checkpoint_requests.json")
OUTPUT_ROOT = Path("/app/output")
FRAMES_ROOT = OUTPUT_ROOT / "checkpoint_frames"
REPORT_PATH = OUTPUT_ROOT / "checkpoint_audit_report.json"


def probe_video(video_path: Path) -> tuple[float, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return fps, total_frames


def read_frame(video_path: Path, frame_index: int):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"无法读取帧 {frame_index}: {video_path}")
    return frame


def main() -> None:
    plan = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    requests = plan["requests"]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    FRAMES_ROOT.mkdir(parents=True, exist_ok=True)

    cache: dict[Path, tuple[float, int]] = {}
    report_requests = []
    unreachable = []

    for item in requests:
        video_path = Path("/app/input") / item["source_video"]
        if video_path not in cache:
            cache[video_path] = probe_video(video_path)

        fps, total_frames = cache[video_path]
        timestamp = float(item["timestamp_seconds"])
        frame_index = math.floor(timestamp * fps + 1e-9)

        output_file = None
        status = "unreachable"

        if timestamp >= 0 and frame_index < total_frames:
            frame = read_frame(video_path, frame_index)
            store_dir = FRAMES_ROOT / item["store_code"]
            store_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{item['checkpoint_id']}__t{round(timestamp * 1000):06d}.jpg"
            output_path = store_dir / filename
            ok = cv2.imwrite(str(output_path), frame)
            if not ok:
                raise RuntimeError(f"无法写出 JPG: {output_path}")
            output_file = output_path.relative_to(OUTPUT_ROOT).as_posix()
            status = "captured"
        else:
            unreachable.append(item["checkpoint_id"])

        report_requests.append(
            {
                "checkpoint_id": item["checkpoint_id"],
                "store_code": item["store_code"],
                "source_video": item["source_video"],
                "requested_timestamp_seconds": item["timestamp_seconds"],
                "status": status,
                "output_file": output_file,
            }
        )

    report = {
        "audit_id": plan["audit_id"],
        "total_requests": len(requests),
        "captured_count": sum(1 for item in report_requests if item["status"] == "captured"),
        "unreachable_count": len(unreachable),
        "requests": report_requests,
        "unreachable_checkpoints": unreachable,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
