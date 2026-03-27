import csv
import json
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


def main() -> None:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        frames = json.load(f)["frames"]

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_id", "coins", "enemies", "turtles"])
        for frame in frames:
            row = [frame["path"]]
            for _, object_path in OBJECTS:
                row.append(run_counter(frame["path"], object_path))
            writer.writerow(row)


if __name__ == "__main__":
    main()
