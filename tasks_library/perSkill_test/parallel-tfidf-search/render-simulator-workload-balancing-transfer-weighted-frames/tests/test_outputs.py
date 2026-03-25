#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from render_baseline import load_render_frames, run_contiguous_interval_baseline

MODULE_PATH = Path("/root/workspace/render_scheduler.py")
MAKESPAN_RATIO_TARGET = 0.60


def load_candidate_module():
    if not MODULE_PATH.exists():
        pytest.fail("/root/workspace/render_scheduler.py 不存在")

    spec = importlib.util.spec_from_file_location("render_scheduler", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def frames():
    return load_render_frames()


@pytest.fixture(scope="session")
def frame_lookup(frames):
    return {frame.frame_id: frame for frame in frames}


def build_scene_expectations(frames):
    totals = {}
    for frame in frames:
        entry = totals.setdefault(
            frame.scene_id,
            {
                "scene_name": frame.scene_name,
                "frame_count": 0,
                "predicted_cost": 0.0,
                "actual_duration": 0,
            },
        )
        entry["frame_count"] += 1
        entry["predicted_cost"] += frame.predicted_cost
        entry["actual_duration"] += frame.actual_duration

    return {
        scene_id: {
            "scene_name": values["scene_name"],
            "frame_count": values["frame_count"],
            "predicted_cost": round(values["predicted_cost"], 2),
            "actual_duration": values["actual_duration"],
        }
        for scene_id, values in sorted(totals.items())
    }


def test_module_contract():
    module = load_candidate_module()
    assert hasattr(module, "schedule_weighted_frames")


def test_schedule_summary_contract(frames, frame_lookup, tmp_path):
    module = load_candidate_module()
    output_path = tmp_path / "render_schedule_summary.json"

    report = module.schedule_weighted_frames(
        frame_path="/root/workspace/render_frames.csv",
        scene_path="/root/workspace/scene_catalog.json",
        output_path=str(output_path),
        num_workers=4,
    )

    assert output_path.exists()
    saved_report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report == saved_report

    required_top_level = {
        "num_workers",
        "total_frames",
        "total_predicted_cost",
        "total_actual_duration",
        "makespan",
        "worker_summaries",
        "scene_totals",
    }
    assert required_top_level.issubset(report.keys())

    assert report["num_workers"] == 4
    assert report["total_frames"] == len(frames)
    assert math.isclose(
        report["total_predicted_cost"],
        round(sum(frame.predicted_cost for frame in frames), 2),
        rel_tol=0.0,
        abs_tol=1e-9,
    )
    assert report["total_actual_duration"] == sum(frame.actual_duration for frame in frames)
    assert len(report["worker_summaries"]) == 4

    assigned_frame_ids = []
    for worker_id, worker in enumerate(report["worker_summaries"]):
        assert worker["worker_id"] == worker_id
        assert set(
            ["worker_id", "frame_count", "scene_count", "predicted_load", "actual_duration", "frames"]
        ).issubset(worker.keys())

        bucket = [frame_lookup[frame_id] for frame_id in worker["frames"]]
        assigned_frame_ids.extend(worker["frames"])

        assert worker["frame_count"] == len(bucket)
        assert worker["scene_count"] == len({frame.scene_id for frame in bucket})
        assert math.isclose(
            worker["predicted_load"],
            round(sum(frame.predicted_cost for frame in bucket), 2),
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert worker["actual_duration"] == sum(frame.actual_duration for frame in bucket)

    expected_frame_ids = {frame.frame_id for frame in frames}
    assert len(assigned_frame_ids) == len(frames)
    assert len(set(assigned_frame_ids)) == len(frames)
    assert set(assigned_frame_ids) == expected_frame_ids
    assert report["makespan"] == max(worker["actual_duration"] for worker in report["worker_summaries"])

    expected_scene_totals = build_scene_expectations(frames)
    assert report["scene_totals"].keys() == expected_scene_totals.keys()

    for scene_id, expected in expected_scene_totals.items():
        actual = report["scene_totals"][scene_id]
        assert actual["scene_name"] == expected["scene_name"]
        assert actual["frame_count"] == expected["frame_count"]
        assert math.isclose(actual["predicted_cost"], expected["predicted_cost"], rel_tol=0.0, abs_tol=1e-9)
        assert actual["actual_duration"] == expected["actual_duration"]


def test_makespan_beats_contiguous_baseline(tmp_path):
    module = load_candidate_module()
    candidate_report = module.schedule_weighted_frames(
        frame_path="/root/workspace/render_frames.csv",
        scene_path="/root/workspace/scene_catalog.json",
        output_path=str(tmp_path / "candidate_summary.json"),
        num_workers=4,
    )
    baseline_report = run_contiguous_interval_baseline(
        frame_path="/root/workspace/render_frames.csv",
        scene_path="/root/workspace/scene_catalog.json",
        output_path=str(tmp_path / "baseline_summary.json"),
        num_workers=4,
    )

    ratio = candidate_report["makespan"] / baseline_report["makespan"]

    assert candidate_report["makespan"] < baseline_report["makespan"]
    assert ratio <= MAKESPAN_RATIO_TARGET, (
        f"makespan 改善不足: candidate={candidate_report['makespan']}, "
        f"baseline={baseline_report['makespan']}, ratio={ratio:.3f}"
    )
