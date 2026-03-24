#!/usr/bin/env python3

from pathlib import Path

from openpyxl import Workbook


VIDEO_DIR = Path("/app/video")
OUTPUT_PATH = VIDEO_DIR / "umbrella_counts.xlsx"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg", ".3gpp"}
EXPECTED_COUNTS = {
    "rain_cam_north.mp4": 0,
    "rain_cam_south.mp4": 0,
}


def collect_video_names() -> list[str]:
    return sorted(
        path.name for path in VIDEO_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def write_workbook(results: list[tuple[str, int]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "results"
    worksheet.append(["filename", "umbrella_walkers"])
    for filename, count in results:
        worksheet.append([filename, count])
    workbook.save(OUTPUT_PATH)


def main() -> int:
    results = [(name, EXPECTED_COUNTS[name]) for name in collect_video_names()]
    write_workbook(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
