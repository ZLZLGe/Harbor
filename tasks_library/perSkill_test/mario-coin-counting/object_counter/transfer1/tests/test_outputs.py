import json
import os
import re
import subprocess

MANIFEST = "/root/image_manifest.json"
COUNTER = "/root/.codex/skills/object_counter/scripts/count_objects.py"
OUTPUT = "/root/transfer1_presence_summary.json"
OBJECTS = [
    ("coins", "/root/coin.png"),
    ("enemies", "/root/enemy.png"),
    ("turtles", "/root/turtle.png"),
]


def run_counter(frame_path: str, object_path: str) -> int:
    output = subprocess.check_output(
        [
            "python3",
            COUNTER,
            "--tool",
            "count",
            "--input_image",
            frame_path,
            "--object_image",
            object_path,
            "--threshold",
            "0.9",
            "--dedup_min_dist",
            "3",
        ],
        text=True,
    )
    match = re.search(r"There are (\d+) objects", output)
    if not match:
        raise RuntimeError(f"unexpected counter output: {output}")
    return int(match.group(1))


def build_expected() -> dict:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        frames = json.load(f)["frames"]

    stats = []
    for index, frame in enumerate(frames):
        frame_path = frame["path"]
        stats.append(
            {
                "index": index,
                "frame_id": frame_path,
                "coins": run_counter(frame_path, OBJECTS[0][1]),
                "enemies": run_counter(frame_path, OBJECTS[1][1]),
                "turtles": run_counter(frame_path, OBJECTS[2][1]),
            }
        )

    max_enemy = max(stats, key=lambda item: (item["enemies"], -item["index"]))
    return {
        "scenario": "template_presence_audit",
        "frame_order": [item["frame_id"] for item in stats],
        "totals": {
            "coins": sum(item["coins"] for item in stats),
            "enemies": sum(item["enemies"] for item in stats),
            "turtles": sum(item["turtles"] for item in stats),
        },
        "max_enemy_frame": {
            "frame_id": max_enemy["frame_id"],
            "enemies": max_enemy["enemies"],
        },
        "nonzero_turtle_frames": [item["frame_id"] for item in stats if item["turtles"] > 0],
    }


def test_output_exists() -> None:
    assert os.path.isfile(OUTPUT)


def test_summary_matches_expected() -> None:
    with open(OUTPUT, "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload == build_expected()
