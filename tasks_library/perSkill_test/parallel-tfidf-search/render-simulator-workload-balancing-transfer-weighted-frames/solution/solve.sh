#!/bin/bash

set -euo pipefail

cat > /root/workspace/render_scheduler.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import json

from render_baseline import load_render_frames, summarize_assignments


def schedule_weighted_frames(
    frame_path: str = "/root/workspace/render_frames.csv",
    scene_path: str = "/root/workspace/scene_catalog.json",
    output_path: str = "/root/workspace/render_schedule_summary.json",
    num_workers: int = 4,
) -> dict:
    if num_workers <= 0:
        raise ValueError("num_workers must be positive")

    frames = load_render_frames(frame_path=frame_path, scene_path=scene_path)
    assignments = [[] for _ in range(num_workers)]
    predicted_loads = [0.0] * num_workers

    for frame in sorted(frames, key=lambda item: (-item.predicted_cost, item.frame_id)):
        worker_id = min(range(num_workers), key=lambda idx: (predicted_loads[idx], idx))
        assignments[worker_id].append(frame)
        predicted_loads[worker_id] += frame.predicted_cost

    summary = summarize_assignments(assignments, output_path=output_path)
    return summary


if __name__ == "__main__":
    result = schedule_weighted_frames()
    print(json.dumps(result, indent=2))
PY

chmod +x /root/workspace/render_scheduler.py
/root/workspace/render_scheduler.py >/root/workspace/render_schedule_stdout.json
