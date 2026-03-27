#!/usr/bin/env python3
import json
import shutil
from collections import Counter
from pathlib import Path

SPEC_PATH = Path("/root/data/archive_spec.json")
SOURCE_ROOT = Path("/root/project_dump")
TARGET_ROOT = Path("/root/projects_sorted")
OUTPUT_PATH = Path("/root/transfer2_archive_plan.json")


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text())
    records = spec["records"]

    bucket_counts: Counter[str] = Counter()
    project_counts: Counter[str] = Counter()
    destinations: list[str] = []

    for item in records:
        filename = item["file"]
        bucket = item["bucket"]
        project = item["project"]

        src = SOURCE_ROOT / filename
        if not src.exists():
            raise FileNotFoundError(f"Missing source file: {src}")

        dst = TARGET_ROOT / bucket / project / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        bucket_counts[bucket] += 1
        project_counts[project] += 1
        destinations.append(str(dst))

    report = {
        "total_files": len(records),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "project_counts": dict(sorted(project_counts.items())),
        "destinations": sorted(destinations),
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
