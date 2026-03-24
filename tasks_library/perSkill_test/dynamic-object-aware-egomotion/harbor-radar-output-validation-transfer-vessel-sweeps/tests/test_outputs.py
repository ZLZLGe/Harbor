import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path("/root")
SWEEPS_PATH = ROOT / "harbor_radar_sweeps.json"
COMPONENTS_PATH = ROOT / "harbor_echo_components.json"
PRED_JSON = ROOT / "pred_harbor_tracks.json"
PRED_MASKS = ROOT / "pred_harbor_echo_masks.npz"

VALID_LABELS = {"锚泊待命", "沿航道驶入", "沿航道驶离", "右舷转向", "左舷回转"}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
            start, end = indptr[row], indptr[row + 1]
            mask[row, indices[start:end]] = True
        masks.append(mask)
        frame_idx += 1
    return shape, masks, data


def expand_intervals(mapping):
    expanded = {}
    for key, labels in mapping.items():
        start, end = map(int, key.split("->"))
        for interval_idx in range(start, end):
            expanded[interval_idx] = tuple(labels)
    return expanded


def build_expected_masks():
    components = load_json(COMPONENTS_PATH)
    shape = tuple(int(v) for v in components["shape"])
    masks = []
    for scan in components["scans"]:
        mask = np.zeros(shape, dtype=bool)
        for component in scan["components"]:
            if not component["active"]:
                continue
            top = int(component["top"])
            left = int(component["left"])
            height = int(component["height"])
            width = int(component["width"])
            mask[top:top + height, left:left + width] = True
        masks.append(mask)
    return shape, masks


class TestOutputFilesExist:
    def test_track_json_exists(self):
        assert PRED_JSON.exists(), "Missing /root/pred_harbor_tracks.json"

    def test_echo_mask_npz_exists(self):
        assert PRED_MASKS.exists(), "Missing /root/pred_harbor_echo_masks.npz"


class TestTrackIntervals:
    @pytest.fixture
    def pred(self):
        return load_json(PRED_JSON)

    @pytest.fixture
    def sweeps(self):
        return load_json(SWEEPS_PATH)

    def test_interval_keys_and_labels_are_valid(self, pred):
        for key, labels in pred.items():
            assert "->" in key
            start_str, end_str = key.split("->")
            assert start_str.isdigit() and end_str.isdigit()
            assert int(end_str) > int(start_str)
            assert isinstance(labels, list) and len(labels) == 1
            assert labels[0] in VALID_LABELS

    def test_intervals_are_continuous(self, pred, sweeps):
        expected_end = len(sweeps["sampled_scans"]) - 1
        items = sorted(pred.items(), key=lambda item: int(item[0].split("->")[0]))
        cursor = 0
        for key, _ in items:
            start, end = map(int, key.split("->"))
            assert start == cursor, f"Gap or overlap near interval {key}"
            cursor = end
        assert cursor == expected_end

    def test_tracks_match_reference_segments_per_interval(self, pred, sweeps):
        expected = {
            f"{segment['start']}->{segment['end']}": [segment["label"]]
            for segment in sweeps["maneuver_segments"]
        }
        assert expand_intervals(pred) == expand_intervals(expected)


class TestSparseEchoMasks:
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

    def test_csr_structure_is_well_formed(self, pred_masks, expected_masks):
        _, pred_list, raw = pred_masks
        expected_shape, _ = expected_masks
        height, width = expected_shape
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

    def test_dense_roundtrip_matches_active_components_exactly(self, pred_masks, expected_masks):
        _, pred_list, _ = pred_masks
        _, expected_list = expected_masks
        for pred_mask, expected_mask in zip(pred_list, expected_list):
            assert np.array_equal(pred_mask, expected_mask)

    def test_echo_progression_reflects_inbound_then_turn(self, pred_masks):
        _, pred_list, _ = pred_masks
        centroids = []
        for mask in pred_list:
            ys, xs = np.where(mask)
            centroids.append((float(xs.mean()), float(ys.mean())))

        assert centroids[0][0] < centroids[3][0] < centroids[7][0]
        assert centroids[3][1] <= centroids[4][1] < centroids[7][1]
