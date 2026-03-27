import csv
import json
import os
import re
import subprocess

MANIFEST = "/root/image_manifest.json"
COUNTER = "/root/.codex/skills/object_counter/scripts/count_objects.py"
OUTPUT = "/root/similar_counting_results.csv"
OBJECTS = [
    ("coins", "/root/coin.png"),
    ("enemies", "/root/enemy.png"),
    ("turtles", "/root/turtle.png"),
]


def run_counter(frame_path: str, object_path: str) -> str:
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
    return match.group(1)


def build_expected_rows() -> list[dict[str, str]]:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        frames = json.load(f)["frames"]

    rows: list[dict[str, str]] = []
    for frame in frames:
        rows.append(
            {
                "frame_id": frame["path"],
                "coins": run_counter(frame["path"], OBJECTS[0][1]),
                "enemies": run_counter(frame["path"], OBJECTS[1][1]),
                "turtles": run_counter(frame["path"], OBJECTS[2][1]),
            }
        )
    return rows


def test_output_exists() -> None:
    assert os.path.isfile(OUTPUT)


def test_csv_matches_expected() -> None:
    with open(OUTPUT, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["frame_id", "coins", "enemies", "turtles"]
        rows = list(reader)

    assert rows == build_expected_rows()
