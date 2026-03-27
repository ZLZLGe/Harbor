#!/usr/bin/env python3
import json
import shutil
from pathlib import Path

CONFIG_PATH = Path("/root/data/expected_layout.json")
SOURCE_ROOT = Path("/root/inbox")
TARGET_ROOT = Path("/root/library")
REPORT_PATH = Path("/root/similar_sort_report.json")


def main() -> None:
    mapping = json.loads(CONFIG_PATH.read_text())

    moved = 0
    folder_counts: dict[str, int] = {}

    for folder, filenames in mapping.items():
        dest_dir = TARGET_ROOT / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            src = SOURCE_ROOT / filename
            if not src.exists():
                raise FileNotFoundError(f"Missing source file: {src}")
            dst = dest_dir / filename
            shutil.move(str(src), str(dst))
            moved += 1
        folder_counts[folder] = len(filenames)

    report = {
        "total_files": sum(len(files) for files in mapping.values()),
        "moved_files": moved,
        "folders": folder_counts,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
