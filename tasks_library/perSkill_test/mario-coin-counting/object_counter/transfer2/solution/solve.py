import json
import re
import subprocess

MANIFEST = "/root/image_manifest.json"
COUNTER = "/root/.codex/skills/object_counter/scripts/count_objects.py"
OUTPUT = "/root/transfer2_shift_report.md"
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

    rows = []
    for frame in frames:
        frame_path = frame["path"]
        coins = run_counter(frame_path, OBJECTS[0][1])
        enemies = run_counter(frame_path, OBJECTS[1][1])
        turtles = run_counter(frame_path, OBJECTS[2][1])
        risk = coins + 2 * enemies + 3 * turtles
        rows.append(
            {
                "frame_id": frame_path,
                "coins": coins,
                "enemies": enemies,
                "turtles": turtles,
                "risk_score": risk,
            }
        )

    highest = max(rows, key=lambda item: item["risk_score"])

    lines = [
        "# Template Presence Report",
        "",
        "| frame_id | coins | enemies | turtles | risk_score |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['frame_id']} | {row['coins']} | {row['enemies']} | {row['turtles']} | {row['risk_score']} |"
        )
    lines.extend(["", f"Highest risk frame: {highest['frame_id']}"])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
