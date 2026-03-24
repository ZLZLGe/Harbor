import json
from pathlib import Path

import cv2

ROOT = Path("/root")
PRED_PATH = ROOT / "pred_line_state_spans.json"
GT_PATH = ROOT / "expected_state_spans.json"
VIDEO_PATH = ROOT / "input.mp4"

TARGET_FPS = 5.0
VALID_LABELS = {"Empty", "Flowing", "Backlog"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def expand_spans(spans: dict) -> dict[int, str]:
    expanded = {}
    for key, values in spans.items():
        assert "->" in key, f"invalid interval key: {key}"
        start_text, end_text = key.split("->", 1)
        assert start_text.isdigit() and end_text.isdigit(), f"non-integer interval key: {key}"
        start = int(start_text)
        end = int(end_text)
        assert start < end, f"interval must satisfy start < end: {key}"
        assert isinstance(values, list) and len(values) == 1, f"each interval must map to a single label array: {key}"
        label = values[0]
        assert label in VALID_LABELS, f"invalid label: {label}"
        for sample_idx in range(start, end):
            assert sample_idx not in expanded, f"overlapping intervals at sample {sample_idx}"
            expanded[sample_idx] = label
    return expanded


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
    assert PRED_PATH.exists(), "missing /root/pred_line_state_spans.json"


def test_spans_cover_every_sample_exactly_once():
    pred = load_json(PRED_PATH)
    expanded = expand_spans(pred)
    sample_ids = compute_sample_ids(VIDEO_PATH, TARGET_FPS)
    assert sorted(expanded) == list(range(len(sample_ids))), "intervals must cover every sampled index exactly once"


def test_predicted_spans_match_expected_timeline():
    pred = load_json(PRED_PATH)
    gt = load_json(GT_PATH)

    pred_expanded = expand_spans(pred)
    gt_expanded = expand_spans(gt)

    assert pred_expanded == gt_expanded, "state labels or interval boundaries do not match the conveyor timeline"


def test_transition_boundaries_align_with_sampled_frame_ids():
    pred = load_json(PRED_PATH)
    sample_ids = compute_sample_ids(VIDEO_PATH, TARGET_FPS)

    transition_samples = []
    for key in pred:
        _, end_text = key.split("->", 1)
        end = int(end_text)
        if end < len(sample_ids):
            transition_samples.append(end)

    assert transition_samples == [5, 16, 24, 31]
    assert [sample_ids[idx] for idx in transition_samples] == [15, 48, 72, 93]
