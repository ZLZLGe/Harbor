import json
import os
import re
import subprocess

MANIFEST = "/root/image_manifest.json"
COUNTER = "/root/.codex/skills/object_counter/scripts/count_objects.py"
OUTPUT = "/root/transfer3_ranked_scoreboard.tsv"
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


def bucket(score: int) -> str:
    if score >= 10:
        return "critical"
    if score >= 4:
        return "medium"
    return "low"


def build_expected_tsv() -> str:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        frames = json.load(f)["frames"]

    rows = []
    for frame in frames:
        frame_path = frame["path"]
        coins = run_counter(frame_path, OBJECTS[0][1])
        enemies = run_counter(frame_path, OBJECTS[1][1])
        turtles = run_counter(frame_path, OBJECTS[2][1])
        score = coins * 2 + enemies * 3 + turtles * 4
        rows.append(
            {
                "frame_id": frame_path,
                "coins": coins,
                "enemies": enemies,
                "turtles": turtles,
                "score": score,
                "bucket": bucket(score),
            }
        )

    rows.sort(key=lambda item: (-item["score"], item["frame_id"]))

    lines = ["rank\tframe_id\tcoins\tenemies\tturtles\tscore\tbucket"]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"{idx}\t{row['frame_id']}\t{row['coins']}\t{row['enemies']}\t{row['turtles']}\t{row['score']}\t{row['bucket']}"
        )
    return "\n".join(lines) + "\n"


def test_output_exists() -> None:
    assert os.path.isfile(OUTPUT)


def test_tsv_matches_expected() -> None:
    with open(OUTPUT, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == build_expected_tsv()
