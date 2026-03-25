#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FRAME_PATH = "/root/workspace/render_frames.csv"
DEFAULT_SCENE_PATH = "/root/workspace/scene_catalog.json"


@dataclass(frozen=True)
class FrameRecord:
    frame_id: int
    scene_id: str
    scene_name: str
    shot_code: str
    predicted_cost: float
    actual_duration: int


def load_scene_catalog(scene_path: str = DEFAULT_SCENE_PATH) -> dict[str, dict]:
    payload = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    return {scene["scene_id"]: scene for scene in payload["scenes"]}


def load_render_frames(
    frame_path: str = DEFAULT_FRAME_PATH,
    scene_path: str = DEFAULT_SCENE_PATH,
) -> list[FrameRecord]:
    scenes = load_scene_catalog(scene_path)
    frames: list[FrameRecord] = []

    with Path(frame_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            scene = scenes[row["scene_id"]]
            frames.append(
                FrameRecord(
                    frame_id=int(row["frame_id"]),
                    scene_id=row["scene_id"],
                    scene_name=scene["scene_name"],
                    shot_code=row["shot_code"],
                    predicted_cost=float(row["predicted_cost"]),
                    actual_duration=int(row["actual_duration"]),
                )
            )

    frames.sort(key=lambda frame: frame.frame_id)
    return frames


def contiguous_partition(frames: list[FrameRecord], num_workers: int) -> list[list[FrameRecord]]:
    if num_workers <= 0:
        raise ValueError("num_workers must be positive")

    base_size, remainder = divmod(len(frames), num_workers)
    assignments: list[list[FrameRecord]] = []
    cursor = 0

    for worker_id in range(num_workers):
        size = base_size + (1 if worker_id < remainder else 0)
        assignments.append(frames[cursor : cursor + size])
        cursor += size

    return assignments


def summarize_assignments(
    assignments: list[list[FrameRecord]],
    output_path: str | None = None,
) -> dict:
    all_frames = [frame for bucket in assignments for frame in bucket]
    scene_totals_raw: dict[str, dict] = {}
    worker_summaries = []

    for worker_id, bucket in enumerate(assignments):
        predicted_load = sum(frame.predicted_cost for frame in bucket)
        actual_duration = sum(frame.actual_duration for frame in bucket)
        scene_ids = {frame.scene_id for frame in bucket}

        for frame in bucket:
            scene_entry = scene_totals_raw.setdefault(
                frame.scene_id,
                {
                    "scene_name": frame.scene_name,
                    "frame_count": 0,
                    "predicted_cost": 0.0,
                    "actual_duration": 0,
                },
            )
            scene_entry["frame_count"] += 1
            scene_entry["predicted_cost"] += frame.predicted_cost
            scene_entry["actual_duration"] += frame.actual_duration

        worker_summaries.append(
            {
                "worker_id": worker_id,
                "frame_count": len(bucket),
                "scene_count": len(scene_ids),
                "predicted_load": round(predicted_load, 2),
                "actual_duration": actual_duration,
                "frames": [frame.frame_id for frame in bucket],
            }
        )

    scene_totals = {
        scene_id: {
            "scene_name": values["scene_name"],
            "frame_count": values["frame_count"],
            "predicted_cost": round(values["predicted_cost"], 2),
            "actual_duration": values["actual_duration"],
        }
        for scene_id, values in sorted(scene_totals_raw.items())
    }

    summary = {
        "num_workers": len(assignments),
        "total_frames": len(all_frames),
        "total_predicted_cost": round(sum(frame.predicted_cost for frame in all_frames), 2),
        "total_actual_duration": sum(frame.actual_duration for frame in all_frames),
        "makespan": max((worker["actual_duration"] for worker in worker_summaries), default=0),
        "worker_summaries": worker_summaries,
        "scene_totals": scene_totals,
    }

    if output_path is not None:
        Path(output_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


def run_contiguous_interval_baseline(
    frame_path: str = DEFAULT_FRAME_PATH,
    scene_path: str = DEFAULT_SCENE_PATH,
    output_path: str = "/root/workspace/contiguous_render_schedule.json",
    num_workers: int = 4,
) -> dict:
    frames = load_render_frames(frame_path=frame_path, scene_path=scene_path)
    assignments = contiguous_partition(frames, num_workers=num_workers)
    return summarize_assignments(assignments, output_path=output_path)
