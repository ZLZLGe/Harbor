#!/usr/bin/env python3
import csv
import json
import shutil
from pathlib import Path

PLAN_PATH = Path("/root/data/organization_plan.json")
SOURCE_ROOT = Path("/root/media_drop")
ORGANIZED_ROOT = Path("/root/organized")
REPORT_PATH = Path("/root/transfer1_keep_decisions.csv")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def move_file(src: Path, dst: Path) -> None:
    ensure_parent(dst)
    shutil.move(str(src), str(dst))


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text())
    rows: list[dict[str, str]] = []

    for group_info in plan["duplicate_groups"]:
        group = group_info["group"]
        category = group_info["category"]
        files = sorted(group_info["files"])
        canonical = files[0]

        for name in files:
            src = SOURCE_ROOT / name
            if not src.exists():
                raise FileNotFoundError(f"Missing source file: {src}")
            if name == canonical:
                dst = ORGANIZED_ROOT / category / name
                decision = "keep"
            else:
                dst = ORGANIZED_ROOT / "duplicates" / group / name
                decision = "duplicate"
            move_file(src, dst)
            rows.append({
                "file": name,
                "group": group,
                "decision": decision,
                "target": str(dst),
            })

    for item in plan["unique_files"]:
        name = item["file"]
        category = item["category"]
        src = SOURCE_ROOT / name
        if not src.exists():
            raise FileNotFoundError(f"Missing source file: {src}")
        dst = ORGANIZED_ROOT / category / name
        move_file(src, dst)
        rows.append({
            "file": name,
            "group": "",
            "decision": "unique",
            "target": str(dst),
        })

    rows.sort(key=lambda r: r["file"])
    with REPORT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "group", "decision", "target"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
