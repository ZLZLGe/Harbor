from pathlib import Path

import numpy as np
import pytest

ROOT_DIR = Path("/root")
PRED_PATH = ROOT_DIR / "motile_cells_dyn_masks.npz"
GT_PATH = Path("/tests/motile_cells_dyn_masks_gt.npz")
STATIC_MASK_PATH = Path("/tests/static_cells_mask.npy")


def load_sparse_masks(path: Path) -> tuple[tuple[int, int], list[np.ndarray]]:
    data = np.load(path)
    shape = tuple(data["shape"].astype(int))
    masks = []
    frame_index = 0
    while f"f_{frame_index}_data" in data:
        indices = data[f"f_{frame_index}_indices"]
        indptr = data[f"f_{frame_index}_indptr"]
        mask = np.zeros(shape, dtype=bool)
        for row in range(shape[0]):
            start = int(indptr[row])
            end = int(indptr[row + 1])
            mask[row, indices[start:end]] = True
        masks.append(mask)
        frame_index += 1
    return shape, masks


def frame_iou(pred: np.ndarray, gt: np.ndarray) -> float:
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    return float(intersection / union) if union > 0 else 1.0


def frame_dice(pred: np.ndarray, gt: np.ndarray) -> float:
    intersection = np.logical_and(pred, gt).sum()
    denom = pred.sum() + gt.sum()
    return float((2 * intersection) / denom) if denom > 0 else 1.0


def centroid(mask: np.ndarray) -> tuple[float, float] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return float(xs.mean()), float(ys.mean())


class TestOutputExists:
    def test_mask_file_exists(self):
        assert PRED_PATH.exists(), "Missing /root/motile_cells_dyn_masks.npz"


class TestSparseLayout:
    @pytest.fixture(scope="class")
    def pred_npz(self):
        return np.load(PRED_PATH)

    @pytest.fixture(scope="class")
    def gt_shape_and_masks(self):
        return load_sparse_masks(GT_PATH)

    def test_shape_present(self, pred_npz):
        assert "shape" in pred_npz

    def test_shape_matches_reference(self, pred_npz, gt_shape_and_masks):
        gt_shape, _ = gt_shape_and_masks
        assert tuple(pred_npz["shape"].astype(int)) == gt_shape

    def test_frame_count_matches_reference(self, pred_npz, gt_shape_and_masks):
        _, gt_masks = gt_shape_and_masks
        frame_count = 0
        while f"f_{frame_count}_data" in pred_npz:
            frame_count += 1
        assert frame_count == len(gt_masks)

    def test_each_frame_has_valid_csr_components(self, pred_npz):
        h, w = tuple(pred_npz["shape"].astype(int))
        frame_count = 0
        while f"f_{frame_count}_data" in pred_npz:
            data = pred_npz[f"f_{frame_count}_data"]
            indices = pred_npz[f"f_{frame_count}_indices"]
            indptr = pred_npz[f"f_{frame_count}_indptr"]
            assert data.ndim == 1
            assert indices.ndim == 1
            assert indptr.ndim == 1
            assert data.shape == indices.shape
            assert indptr.shape[0] == h + 1
            assert int(indptr[0]) == 0
            assert np.all(indptr[1:] >= indptr[:-1])
            assert int(indptr[-1]) == indices.shape[0]
            assert np.all(indices >= 0)
            assert np.all(indices < w)
            frame_count += 1
        assert frame_count > 0


class TestMaskBehavior:
    @pytest.fixture(scope="class")
    def pred_masks(self):
        return load_sparse_masks(PRED_PATH)

    @pytest.fixture(scope="class")
    def gt_masks(self):
        return load_sparse_masks(GT_PATH)

    @pytest.fixture(scope="class")
    def static_mask(self):
        return np.load(STATIC_MASK_PATH).astype(bool)

    def test_has_foreground_pixels(self, pred_masks):
        _, masks = pred_masks
        assert sum(int(mask.sum()) for mask in masks) > 0

    def test_overlap_metrics_on_active_frames(self, pred_masks, gt_masks):
        _, pred = pred_masks
        _, gt = gt_masks
        ious = []
        dices = []
        for pred_mask, gt_mask in zip(pred, gt):
            if int(gt_mask.sum()) > 850:
                ious.append(frame_iou(pred_mask, gt_mask))
                dices.append(frame_dice(pred_mask, gt_mask))
        assert ious
        assert float(np.mean(ious)) >= 0.08
        assert float(np.median(dices)) >= 0.18

    def test_active_frame_recall(self, pred_masks, gt_masks):
        _, pred = pred_masks
        _, gt = gt_masks
        gt_active = 0
        recovered = 0
        for pred_mask, gt_mask in zip(pred, gt):
            if int(gt_mask.sum()) > 900:
                gt_active += 1
                if int(np.logical_and(pred_mask, gt_mask).sum()) > 120:
                    recovered += 1
        recall = recovered / gt_active if gt_active else 1.0
        assert recall >= 0.55

    def test_centroid_tracks_motile_cells(self, pred_masks, gt_masks):
        _, pred = pred_masks
        _, gt = gt_masks
        distances = []
        for pred_mask, gt_mask in zip(pred, gt):
            pred_center = centroid(pred_mask)
            gt_center = centroid(gt_mask)
            if pred_center is None or gt_center is None:
                continue
            dx = pred_center[0] - gt_center[0]
            dy = pred_center[1] - gt_center[1]
            distances.append(float(np.hypot(dx, dy)))
        assert distances
        assert float(np.median(distances)) <= 40.0

    def test_static_cells_are_mostly_suppressed(self, pred_masks, static_mask):
        _, pred = pred_masks
        predicted_total = sum(int(mask.sum()) for mask in pred)
        static_overlap = sum(int(np.logical_and(mask, static_mask).sum()) for mask in pred)
        assert predicted_total > 0
        assert static_overlap / predicted_total <= 0.25
