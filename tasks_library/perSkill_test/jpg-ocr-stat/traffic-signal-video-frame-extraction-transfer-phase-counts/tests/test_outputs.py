import json
from pathlib import Path

import cv2


OUTPUT_PATH = Path("/app/workspace/traffic_phase_counts.json")
WORKSPACE = Path("/app/workspace")
VIDEO_DIR = WORKSPACE / "traffic_videos"
CONFIG_PATH = WORKSPACE / "traffic_signal_config.json"
EXPECTED = {
    "sample_interval_seconds": 2,
    "videos": [
        {
            "video_file": "junction_cedar.avi",
            "sampled_frames_dir": "sampled_frames/junction_cedar",
            "sampled_frame_count": 6,
            "phase_counts": {
                "northbound": {"red": 3, "yellow": 1, "green": 2},
                "eastbound": {"red": 2, "yellow": 2, "green": 2},
            },
        },
        {
            "video_file": "junction_market.avi",
            "sampled_frames_dir": "sampled_frames/junction_market",
            "sampled_frame_count": 6,
            "phase_counts": {
                "northbound": {"red": 2, "yellow": 1, "green": 3},
                "eastbound": {"red": 2, "yellow": 1, "green": 3},
            },
        },
        {
            "video_file": "junction_river.avi",
            "sampled_frames_dir": "sampled_frames/junction_river",
            "sampled_frame_count": 6,
            "phase_counts": {
                "northbound": {"red": 2, "yellow": 2, "green": 2},
                "eastbound": {"red": 3, "yellow": 2, "green": 1},
            },
        },
    ],
}


def read_all_frames(video_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), f"failed to open video: {video_path}"
    fps = cap.get(cv2.CAP_PROP_FPS)
    assert fps > 0, f"invalid FPS for {video_path}: {fps}"

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    assert frames, f"video has no readable frames: {video_path}"
    return fps, frames


def detect_state(frame, roi):
    x1, y1, x2, y2 = roi
    crop = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    red_mask = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255)) | cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
    yellow_mask = cv2.inRange(hsv, (18, 80, 80), (40, 255, 255))
    green_mask = cv2.inRange(hsv, (45, 60, 60), (95, 255, 255))

    scores = {
        "red": int(cv2.countNonZero(red_mask)),
        "yellow": int(cv2.countNonZero(yellow_mask)),
        "green": int(cv2.countNonZero(green_mask)),
    }
    return max(scores, key=scores.get)


def mean_absolute_difference(frame_a, frame_b):
    diff = cv2.absdiff(frame_a, frame_b)
    return float(sum(cv2.mean(diff)[:3]) / 3.0)


def expected_sample_indices(frame_count: int, fps: float, interval_seconds: int):
    interval_frame_count = max(1, round(fps * interval_seconds))
    return list(range(0, frame_count, interval_frame_count))


def find_best_matching_frame(actual_frame, source_frames):
    best_index = None
    best_score = None
    for index, source_frame in enumerate(source_frames):
        score = mean_absolute_difference(actual_frame, source_frame)
        if best_score is None or score < best_score:
            best_index = index
            best_score = score
    return best_index, best_score


def assert_counts_schema(video_entry):
    assert set(video_entry.keys()) == {
        "video_file",
        "sampled_frames_dir",
        "sampled_frame_count",
        "phase_counts",
    }, f"video entry fields mismatch: {video_entry.keys()}"
    assert video_entry["sampled_frames_dir"] == f"sampled_frames/{Path(video_entry['video_file']).stem}"

    for direction, counts in video_entry["phase_counts"].items():
        assert set(counts.keys()) == {"red", "yellow", "green"}, f"invalid phase keys for {direction}: {counts.keys()}"
        assert sum(counts.values()) == video_entry["sampled_frame_count"], (
            f"phase counts for {direction} do not sum to sampled_frame_count"
        )


def assert_exported_frames_match_video(video_spec, video_entry, interval_seconds):
    video_path = VIDEO_DIR / video_spec["video_file"]
    fps, source_frames = read_all_frames(video_path)
    sample_indices = expected_sample_indices(len(source_frames), fps, interval_seconds)

    frame_dir = WORKSPACE / video_entry["sampled_frames_dir"]
    assert frame_dir.exists(), f"missing frame directory: {frame_dir}"
    frame_files = sorted(frame_dir.glob("frame_*.jpg"))
    expected_names = [f"frame_{index:03d}.jpg" for index in range(len(sample_indices))]

    assert video_entry["sampled_frame_count"] == len(sample_indices), (
        f"sampled_frame_count mismatch for {video_entry['video_file']}: "
        f"json says {video_entry['sampled_frame_count']}, expected {len(sample_indices)}"
    )
    assert [path.name for path in frame_files] == expected_names, f"unexpected frame names in {frame_dir}"

    computed_counts = {
        signal["direction"]: {"red": 0, "yellow": 0, "green": 0}
        for signal in video_spec["signals"]
    }

    for output_index, frame_path in enumerate(frame_files):
        actual_frame = cv2.imread(str(frame_path))
        assert actual_frame is not None, f"failed to read exported frame: {frame_path}"

        expected_source_index = sample_indices[output_index]
        matched_source_index, best_score = find_best_matching_frame(actual_frame, source_frames)

        assert matched_source_index == expected_source_index, (
            f"{frame_path.name} does not match the required sampled source frame.\n"
            f"Expected source frame index: {expected_source_index}\n"
            f"Best matching source frame index: {matched_source_index}\n"
            f"Best mean absolute pixel difference: {best_score:.4f}"
        )
        assert best_score is not None and best_score <= 10.0, (
            f"{frame_path.name} is too different from its source frame. "
            f"Mean absolute pixel difference: {best_score:.4f}"
        )

        for signal in video_spec["signals"]:
            state = detect_state(actual_frame, signal["roi"])
            computed_counts[signal["direction"]][state] += 1

    assert computed_counts == video_entry["phase_counts"], (
        f"phase_counts do not match the exported frame contents for {video_entry['video_file']}.\n"
        f"From frames: {json.dumps(computed_counts, indent=2, ensure_ascii=False)}\n"
        f"From JSON: {json.dumps(video_entry['phase_counts'], indent=2, ensure_ascii=False)}"
    )


def main():
    assert OUTPUT_PATH.exists(), "missing /app/workspace/traffic_phase_counts.json"

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert set(data.keys()) == {"sample_interval_seconds", "videos"}, f"top-level keys mismatch: {data.keys()}"
    assert data["sample_interval_seconds"] == config["sample_interval_seconds"]
    assert data["sample_interval_seconds"] == EXPECTED["sample_interval_seconds"]

    videos = data["videos"]
    assert isinstance(videos, list), "videos must be a list"
    actual_order = [item["video_file"] for item in videos]
    assert actual_order == sorted(actual_order), f"videos must be sorted by video_file: {actual_order}"

    config_by_name = {item["video_file"]: item for item in config["videos"]}
    for video_entry in videos:
        assert video_entry["video_file"] in config_by_name, f"unexpected video_file: {video_entry['video_file']}"
        assert_counts_schema(video_entry)
        assert_exported_frames_match_video(
            config_by_name[video_entry["video_file"]],
            video_entry,
            data["sample_interval_seconds"],
        )

    assert data == EXPECTED, (
        "traffic_phase_counts.json does not match expected output.\n"
        f"Actual: {json.dumps(data, indent=2, ensure_ascii=False)}\n"
        f"Expected: {json.dumps(EXPECTED, indent=2, ensure_ascii=False)}"
    )


if __name__ == "__main__":
    main()
