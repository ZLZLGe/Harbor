import csv
from pathlib import Path

import cv2

ROOT = Path("/root")
PRED_PATH = ROOT / "pred_queue_counts.csv"
VIDEO_PATH = ROOT / "input.mp4"
TARGET_FPS = 3.0

EXPECTED_COUNTS = [
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    4,
    3,
    2,
    2,
    1,
    0,
    0,
    1,
    2,
    3,
    2,
    1,
]


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def compute_sample_ids(video_path: Path, target_fps: float) -> list[int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    step = max(1, int(round(fps / target_fps)))
    return list(range(0, total_frames, step))


def test_output_file_exists():
    assert PRED_PATH.exists(), "missing /root/pred_queue_counts.csv"


def test_csv_schema_and_length_are_correct():
    header, rows = load_rows(PRED_PATH)
    assert header == ["sample_index", "source_frame_id", "queued_vehicle_count"]
    assert len(rows) == len(EXPECTED_COUNTS)


def test_sample_index_and_source_frame_alignment():
    _, rows = load_rows(PRED_PATH)
    sample_ids = compute_sample_ids(VIDEO_PATH, TARGET_FPS)

    assert len(sample_ids) == len(EXPECTED_COUNTS)
    for expected_index, row in enumerate(rows):
        assert int(row["sample_index"]) == expected_index
        assert int(row["source_frame_id"]) == sample_ids[expected_index]


def test_queue_counts_match_expected_timeline():
    _, rows = load_rows(PRED_PATH)
    counts = [int(row["queued_vehicle_count"]) for row in rows]
    assert counts == EXPECTED_COUNTS


def test_count_profile_matches_red_green_cycles():
    _, rows = load_rows(PRED_PATH)
    counts = [int(row["queued_vehicle_count"]) for row in rows]

    assert counts[8:10] == [4, 4]
    assert counts[14:16] == [0, 0]
    assert counts[-5:] == [1, 2, 3, 2, 1]
