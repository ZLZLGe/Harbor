import json
from pathlib import Path

import pytest

ROOT = Path("/root")
OUTPUT_PATH = ROOT / "egomotion_segments.json"

VALID_LABELS = [
    "Stay",
    "Dolly In",
    "Dolly Out",
    "Pan Left",
    "Pan Right",
    "Tilt Up",
    "Tilt Down",
    "Roll Left",
    "Roll Right",
]
VALID_LABEL_SET = set(VALID_LABELS)

# Manually annotated from the fixed input clip at the task's sampling rate.
# The camera advances forward throughout the route, and the last sampled step
# also includes a slight rightward pan as the view opens toward the street.
GROUND_TRUTH_TIMELINE = {
    "0->16": ["Dolly In"],
    "16->17": ["Dolly In", "Pan Right"],
}


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def parse_intervals(data: dict):
    intervals = []
    for key, labels in data.items():
        if "->" not in key:
            raise AssertionError(f"invalid interval key: {key}")
        start_str, end_str = key.split("->", 1)
        if not start_str.isdigit() or not end_str.isdigit():
            raise AssertionError(f"interval must use integers: {key}")
        start, end = int(start_str), int(end_str)
        if end <= start:
            raise AssertionError(f"invalid half-open interval: {key}")
        if not isinstance(labels, list) or not labels:
            raise AssertionError(f"labels for {key} must be a non-empty list")
        if len(labels) != len(set(labels)):
            raise AssertionError(f"labels for {key} contain duplicates")
        unknown = set(labels) - VALID_LABEL_SET
        if unknown:
            raise AssertionError(f"labels for {key} contain invalid values: {sorted(unknown)}")
        intervals.append((start, end, tuple(labels)))
    intervals.sort(key=lambda item: item[0])
    return intervals


def expand(intervals):
    expanded = {}
    for start, end, labels in intervals:
        for step in range(start, end):
            expanded[step] = set(labels)
    return expanded


def macro_f1(pred_steps: dict, gt_steps: dict):
    labels_in_gt = sorted({label for labels in gt_steps.values() for label in labels})
    scores = []
    all_steps = sorted(set(pred_steps) | set(gt_steps))
    for label in labels_in_gt:
        tp = fp = fn = 0
        for step in all_steps:
            pred_has = label in pred_steps.get(step, set())
            gt_has = label in gt_steps.get(step, set())
            if pred_has and gt_has:
                tp += 1
            elif pred_has and not gt_has:
                fp += 1
            elif gt_has and not pred_has:
                fn += 1
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return sum(scores) / len(scores)


@pytest.fixture(scope="module")
def pred_data():
    assert OUTPUT_PATH.exists(), "missing /root/egomotion_segments.json"
    return load_json(OUTPUT_PATH)


@pytest.fixture(scope="module")
def gt_data():
    return GROUND_TRUTH_TIMELINE


def test_root_is_object(pred_data):
    assert isinstance(pred_data, dict)
    assert pred_data


def test_intervals_cover_all_steps_without_overlap(pred_data, gt_data):
    pred_intervals = parse_intervals(pred_data)
    gt_intervals = parse_intervals(gt_data)

    assert pred_intervals[0][0] == 0
    assert pred_intervals[-1][1] == gt_intervals[-1][1]

    cursor = 0
    for start, end, _ in pred_intervals:
        assert start == cursor, f"expected contiguous coverage, got gap or overlap before {start}"
        cursor = end


def test_adjacent_intervals_are_compressed(pred_data):
    pred_intervals = parse_intervals(pred_data)
    for idx in range(1, len(pred_intervals)):
        assert pred_intervals[idx - 1][2] != pred_intervals[idx][2]


def test_timeline_macro_f1(pred_data, gt_data):
    pred_steps = expand(parse_intervals(pred_data))
    gt_steps = expand(parse_intervals(gt_data))
    score = macro_f1(pred_steps, gt_steps)
    assert score >= 0.85, f"macro F1 too low: {score:.4f}"
