import csv
from pathlib import Path

import cv2
import json


WORKSPACE = Path("/app/workspace")
OUTPUT_CSV = WORKSPACE / "slide_change_index.csv"
CONFIG_PATH = WORKSPACE / "lecture_assets" / "lecture_capture_config.json"
EXPECTED_ROWS = [
    ("00:00:04", "slide_change_previews/change_01.jpg"),
    ("00:00:09", "slide_change_previews/change_02.jpg"),
    ("00:00:13", "slide_change_previews/change_03.jpg"),
]
EXPECTED_MARKERS = {
    "slide_change_previews/change_01.jpg": (70, 175, 55),
    "slide_change_previews/change_02.jpg": (0, 145, 255),
    "slide_change_previews/change_03.jpg": (35, 35, 215),
}


def read_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def assert_marker_color(image_path: Path, expected_bgr: tuple[int, int, int]) -> None:
    image = cv2.imread(str(image_path))
    assert image is not None, f"cannot read preview frame: {image_path}"

    badge = image[64:114, 64:114]
    assert badge.size > 0, f"badge crop is empty for {image_path}"
    mean_bgr = badge.mean(axis=(0, 1))

    for idx, channel_name in enumerate(["blue", "green", "red"]):
        actual = float(mean_bgr[idx])
        expected = float(expected_bgr[idx])
        assert abs(actual - expected) <= 15.0, (
            f"badge color mismatch for {image_path} on {channel_name} channel: "
            f"actual={actual:.2f}, expected={expected:.2f}"
        )


def main() -> None:
    assert OUTPUT_CSV.exists(), "missing /app/workspace/slide_change_index.csv"

    rows = read_rows(OUTPUT_CSV)
    assert rows, "slide_change_index.csv is empty"
    assert rows[0] == ["timestamp", "preview_frame"], f"unexpected header: {rows[0]}"
    assert rows[1:] == [list(item) for item in EXPECTED_ROWS], (
        "slide_change_index.csv content mismatch.\n"
        f"Actual: {rows[1:]}\n"
        f"Expected: {EXPECTED_ROWS}"
    )

    timestamps = [row[0] for row in rows[1:]]
    assert timestamps == sorted(timestamps), f"timestamps must be sorted: {timestamps}"
    assert "00:00:00" not in timestamps, "initial slide must not be recorded as a change"

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["preview_dir"] == "slide_change_previews", f"unexpected preview_dir: {config['preview_dir']}"

    for _, preview_rel in EXPECTED_ROWS:
        preview_path = WORKSPACE / preview_rel
        assert preview_path.exists(), f"missing preview frame: {preview_path}"
        assert preview_path.stat().st_size > 0, f"preview frame is empty: {preview_path}"
        assert_marker_color(preview_path, EXPECTED_MARKERS[preview_rel])


if __name__ == "__main__":
    main()
