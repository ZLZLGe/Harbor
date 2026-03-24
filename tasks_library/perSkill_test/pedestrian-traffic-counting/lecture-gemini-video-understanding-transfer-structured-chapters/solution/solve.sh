#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os

output_path = os.environ.get("TASK_OUTPUT_FILE", "/app/lecture/chapter_outline.json")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

result = {
    "video": "session_alpha.avi",
    "overall_summary": (
        "The lecture explains why motion cues help track people, derives frame differencing on the "
        "whiteboard, demonstrates how block occlusion can hide motion, and finishes with a short "
        "question-and-answer exchange about lighting and shadows."
    ),
    "chapters": [
        {
            "start_time": "00:00",
            "end_time": "00:12",
            "title": "Why motion cues matter for tracking",
            "mode": "讲台讲解",
        },
        {
            "start_time": "00:12",
            "end_time": "00:24",
            "title": "Whiteboard derivation of frame differencing",
            "mode": "白板书写",
        },
        {
            "start_time": "00:24",
            "end_time": "00:36",
            "title": "Block demo for occlusion",
            "mode": "实物演示",
        },
        {
            "start_time": "00:36",
            "end_time": "00:48",
            "title": "Questions about lighting and shadows",
            "mode": "问答",
        },
    ],
}

with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
