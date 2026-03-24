import csv
import json
import os
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
MANIFEST_PATH = ROOT / "wildfire_sampling_manifest.csv"
RUNS_PATH = ROOT / "wildfire_fireline_runs.json"
PRED_JSON = ROOT / "pred_fire_progression.json"
PRED_MASKS = ROOT / "pred_fireline_masks.npz"

VALID_LABELS = {"初始点火", "顺风扩展", "峡谷跃进", "侧翼回燃"}


def load_manifest():
    with open(MANIFEST_PATH, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["sample_index"] = int(row["sample_index"])
        row["front_edge_col"] = int(row["front_edge_col"])
        row["wind_kph"] = int(row["wind_kph"])
    return rows


def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_sparse_masks(path: Path):
    data = np.load(path)
    shape = tuple(data["shape"].astype(int))
    masks = []
    frame_idx = 0
    while f"f_{frame_idx}_data" in data:
        indices = data[f"f_{frame_idx}_indices"]
        indptr = data[f"f_{frame_idx}_indptr"]
        mask = np.zeros(shape, dtype=bool)
        for row in range(len(indptr) - 1):
            start, end = int(indptr[row]), int(indptr[row + 1])
            mask[row, indices[start:end]] = True
        masks.append(mask)
        frame_idx += 1
    return shape, masks, data


def build_expected_segments(rows):
    phase_rows = [
        (row["sample_index"], row["phase_to_next"])
        for row in rows
        if row["phase_to_next"]
    ]
    merged = {}
    start_idx, current_label = phase_rows[0]
    previous_idx = start_idx

    for sample_index, label in phase_rows[1:]:
        if label != current_label:
            merged[f"{start_idx}->{previous_idx + 1}"] = [current_label]
            start_idx = sample_index
            current_label = label
        previous_idx = sample_index

    merged[f"{start_idx}->{previous_idx + 1}"] = [current_label]
    return merged


def build_expected_masks():
    payload = load_json(RUNS_PATH)
    shape = tuple(int(v) for v in payload["shape"])
    masks = []
    for snapshot in sorted(payload["snapshots"], key=lambda item: int(item["sample_index"])):
        mask = np.zeros(shape, dtype=bool)
        for segment in snapshot["segments"]:
            row = int(segment["row"])
            for start, end in segment["col_ranges"]:
                mask[row, int(start):int(end)] = True
        masks.append(mask)
    return shape, masks


def expand_intervals(mapping):
    expanded = {}
    for key, labels in mapping.items():
        start, end = map(int, key.split("->"))
        for interval_idx in range(start, end):
            expanded[interval_idx] = tuple(labels)
    return expanded


class TestOutputFilesExist:
    def test_progression_json_exists(self):
        assert PRED_JSON.exists(), "Missing /root/pred_fire_progression.json"

    def test_mask_npz_exists(self):
        assert PRED_MASKS.exists(), "Missing /root/pred_fireline_masks.npz"


class TestFireProgression:
    @pytest.fixture
    def manifest_rows(self):
        return load_manifest()

    @pytest.fixture
    def pred(self):
        return load_json(PRED_JSON)

    def test_keys_and_labels_are_valid(self, pred):
        for key, labels in pred.items():
            assert "->" in key
            start_str, end_str = key.split("->")
            assert start_str.isdigit() and end_str.isdigit()
            assert int(end_str) > int(start_str)
            assert isinstance(labels, list) and len(labels) == 1
            assert labels[0] in VALID_LABELS

    def test_intervals_cover_all_sample_gaps(self, pred, manifest_rows):
        expected_end = len(manifest_rows) - 1
        items = sorted(pred.items(), key=lambda item: int(item[0].split("->")[0]))
        cursor = 0
        for key, _ in items:
            start, end = map(int, key.split("->"))
            assert start == cursor, f"Gap or overlap near interval {key}"
            cursor = end
        assert cursor == expected_end

    def test_progression_matches_manifest_runs(self, pred, manifest_rows):
        expected = build_expected_segments(manifest_rows)
        assert expand_intervals(pred) == expand_intervals(expected)


class TestSparseFirelineMasks:
    @pytest.fixture
    def pred_masks(self):
        return load_sparse_masks(PRED_MASKS)

    @pytest.fixture
    def expected_masks(self):
        return build_expected_masks()

    def test_shape_and_frame_count_match_inputs(self, pred_masks, expected_masks):
        pred_shape, pred_list, _ = pred_masks
        expected_shape, expected_list = expected_masks
        assert pred_shape == expected_shape
        assert len(pred_list) == len(expected_list) == 8

    def test_csr_components_are_well_formed(self, pred_masks):
        shape, pred_list, raw = pred_masks
        height, width = shape
        for frame_idx in range(len(pred_list)):
            data = raw[f"f_{frame_idx}_data"]
            indices = raw[f"f_{frame_idx}_indices"]
            indptr = raw[f"f_{frame_idx}_indptr"]
            assert indptr.shape == (height + 1,)
            assert int(indptr[0]) == 0
            assert np.all(np.diff(indptr) >= 0)
            assert int(indptr[-1]) == len(indices) == len(data)
            if len(indices):
                assert int(indices.min()) >= 0
                assert int(indices.max()) < width
                assert np.all(data.astype(bool))

    def test_dense_roundtrip_matches_fireline_runs_exactly(self, pred_masks, expected_masks):
        _, pred_list, _ = pred_masks
        _, expected_list = expected_masks
        for pred_mask, expected_mask in zip(pred_list, expected_list):
            assert np.array_equal(pred_mask, expected_mask)

    def test_front_advances_downwind_then_flank_fire_fades(self, pred_masks):
        _, pred_list, _ = pred_masks
        east_edges = []
        upper_band_pixels = []
        active_counts = []
        for mask in pred_list:
            ys, xs = np.where(mask)
            east_edges.append(int(xs.max()))
            upper_band_pixels.append(int(mask[:4].sum()))
            active_counts.append(int(mask.sum()))

        assert east_edges[0] < east_edges[2] < east_edges[5]
        assert upper_band_pixels[:3] == [0, 0, 0]
        assert upper_band_pixels[3] > 0 and upper_band_pixels[4] > upper_band_pixels[3]
        assert upper_band_pixels[-1] == 0
        assert active_counts[0] < active_counts[4] < active_counts[6]
        assert active_counts[-1] < active_counts[6]
