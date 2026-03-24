import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path("/root")
OBS_PATH = ROOT / "cell_migration_observations.json"
REF_MASKS_PATH = ROOT / "cell_migration_dense_masks.npz"
PRED_JSON = ROOT / "pred_cell_activity.json"
PRED_MASKS = ROOT / "pred_cell_activity_masks.npz"

VALID_LABELS = {"静止扩张", "定向迁移", "快速汇合"}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_reference():
    observations = load_json(OBS_PATH)
    dense_masks = np.load(REF_MASKS_PATH)
    num_frames = len(observations["sampled_frames"])
    reference_masks = [
        dense_masks[f"frame_{frame_idx}"].astype(bool)
        for frame_idx in range(num_frames)
    ]
    return observations, reference_masks, tuple(dense_masks["shape"].astype(int))


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


class TestOutputFilesExist:
    def test_json_exists(self):
        assert PRED_JSON.exists(), "Missing /root/pred_cell_activity.json"

    def test_mask_npz_exists(self):
        assert PRED_MASKS.exists(), "Missing /root/pred_cell_activity_masks.npz"


class TestIntervalOutput:
    @pytest.fixture
    def pred(self):
        return load_json(PRED_JSON)

    @pytest.fixture
    def observations(self):
        observations, _, _ = load_reference()
        return observations

    def test_keys_and_labels_are_valid(self, pred):
        for key, labels in pred.items():
            assert "->" in key
            start_str, end_str = key.split("->")
            assert start_str.isdigit() and end_str.isdigit()
            assert int(end_str) > int(start_str)
            assert isinstance(labels, list) and len(labels) == 1
            assert labels[0] in VALID_LABELS

    def test_intervals_cover_all_sample_intervals(self, pred, observations):
        expected_end = len(observations["sampled_frames"]) - 1
        items = sorted(pred.items(), key=lambda item: int(item[0].split("->")[0]))
        cursor = 0
        for key, _ in items:
            start, end = map(int, key.split("->"))
            assert start == cursor, f"Gap or overlap near interval {key}"
            cursor = end
        assert cursor == expected_end

    def test_interval_labels_match_observation_segments(self, pred, observations):
        expected = {
            f"{segment['start']}->{segment['end']}": [segment["label"]]
            for segment in observations["state_segments"]
        }
        assert expand_intervals(pred) == expand_intervals(expected)


class TestSparseMasks:
    @pytest.fixture
    def reference(self):
        return load_reference()

    @pytest.fixture
    def pred_masks(self):
        return load_sparse_masks(PRED_MASKS)

    def test_shape_and_frame_count_match_reference(self, reference, pred_masks):
        observations, reference_masks, reference_shape = reference
        pred_shape, pred_list, _ = pred_masks
        assert pred_shape == reference_shape
        assert len(pred_list) == len(observations["sampled_frames"]) == len(reference_masks)

    def test_csr_components_are_consecutive_and_well_formed(self, reference, pred_masks):
        _, _, reference_shape = reference
        height, width = reference_shape
        _, pred_list, raw_data = pred_masks

        for frame_idx in range(len(pred_list)):
            data = raw_data[f"f_{frame_idx}_data"]
            indices = raw_data[f"f_{frame_idx}_indices"]
            indptr = raw_data[f"f_{frame_idx}_indptr"]
            assert indptr.shape == (height + 1,)
            assert int(indptr[0]) == 0
            assert np.all(np.diff(indptr) >= 0)
            assert int(indptr[-1]) == len(indices) == len(data)
            if len(indices):
                assert int(indices.min()) >= 0
                assert int(indices.max()) < width
                assert np.all(data.astype(bool))

    def test_dense_roundtrip_matches_reference_masks(self, reference, pred_masks):
        _, reference_masks, _ = reference
        _, pred_list, _ = pred_masks

        for pred_mask, ref_mask in zip(pred_list, reference_masks):
            assert np.array_equal(pred_mask, ref_mask)

    def test_active_pixel_counts_follow_expected_trend(self, reference, pred_masks):
        _, reference_masks, _ = reference
        _, pred_list, _ = pred_masks
        pred_counts = [int(mask.sum()) for mask in pred_list]
        ref_counts = [int(mask.sum()) for mask in reference_masks]
        assert pred_counts == ref_counts
        assert pred_counts[0] < pred_counts[4] < pred_counts[-1]
