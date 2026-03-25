import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")
OUTPUT_PATH = ROOT / "rooftop_activity_heatmap.npy"
SPEC_PATH = ROOT / "heatmap_spec.json"
REFERENCE_MASKS_PATH = Path("/tests/reference_sampled_masks.npz")


def load_reference_heatmap() -> np.ndarray:
    data = np.load(REFERENCE_MASKS_PATH)
    shape = tuple(int(v) for v in data["shape"])
    counts = np.zeros(shape, dtype=np.float32)
    frame_idx = 0
    while f"f_{frame_idx}" in data:
        counts += data[f"f_{frame_idx}"].astype(np.float32).reshape(shape)
        frame_idx += 1

    peak = float(counts.max())
    return counts / peak if peak > 0.0 else counts


def box_blur(array: np.ndarray, radius: int = 2) -> np.ndarray:
    padded = np.pad(array, radius, mode="edge")
    out = np.zeros_like(array, dtype=np.float32)
    size = 2 * radius + 1
    area = float(size * size)
    for dy in range(size):
        for dx in range(size):
            out += padded[dy : dy + array.shape[0], dx : dx + array.shape[1]]
    return out / area


def weighted_centroid(array: np.ndarray) -> tuple[float, float]:
    total = float(array.sum())
    yy, xx = np.indices(array.shape, dtype=np.float32)
    if total <= 0.0:
        return float(array.shape[1] / 2.0), float(array.shape[0] / 2.0)
    cx = float((array * xx).sum() / total)
    cy = float((array * yy).sum() / total)
    return cx, cy


def test_output_exists():
    assert OUTPUT_PATH.exists(), "Missing /root/rooftop_activity_heatmap.npy"


def test_shape_range_and_normalization_contract():
    spec = json.loads(SPEC_PATH.read_text())
    heatmap = np.load(OUTPUT_PATH)

    assert heatmap.ndim == 2, "Heatmap must be a 2D array"
    assert tuple(heatmap.shape) == tuple(spec["expected_shape"]), "Heatmap shape does not match heatmap_spec.json"
    assert np.issubdtype(heatmap.dtype, np.floating), "Heatmap must contain floating-point values"
    assert np.isfinite(heatmap).all(), "Heatmap contains NaN or inf values"
    assert float(heatmap.min()) >= -1e-6, "Heatmap values must stay within [0, 1]"
    assert float(heatmap.max()) <= 1.0 + 1e-6, "Heatmap values must stay within [0, 1]"

    peak = float(heatmap.max())
    total = float(heatmap.sum())
    assert total > 0.0, "Heatmap must contain non-zero dynamic activity for this clip"
    assert peak >= 0.95, "Heatmap must be globally normalized by its maximum value"


def test_heatmap_matches_reference_activity_pattern():
    pred = np.load(OUTPUT_PATH).astype(np.float32)
    ref = load_reference_heatmap()

    pred_blur = box_blur(pred)
    ref_blur = box_blur(ref)

    mae = float(np.mean(np.abs(pred_blur - ref_blur)))
    cosine = float(
        np.dot(pred_blur.ravel(), ref_blur.ravel())
        / (np.linalg.norm(pred_blur.ravel()) * np.linalg.norm(ref_blur.ravel()) + 1e-8)
    )

    pred_focus = pred_blur >= 0.35
    ref_focus = ref_blur >= 0.35
    overlap = np.logical_and(pred_focus, ref_focus).sum()
    pred_focus_pixels = int(pred_focus.sum())
    ref_focus_pixels = int(ref_focus.sum())
    precision = float(overlap / pred_focus_pixels) if pred_focus_pixels else 0.0
    recall = float(overlap / ref_focus_pixels) if ref_focus_pixels else 0.0
    mass_ratio = float(pred.sum() / (ref.sum() + 1e-8))

    assert mae <= 0.12, "Blurred heatmap deviates too much from the expected activity map"
    assert cosine >= 0.82, "Heatmap energy is concentrated in the wrong parts of the roof"
    assert precision >= 0.37, "Predicted hot regions spill too far outside the expected activity zones"
    assert recall >= 0.55, "Predicted hot regions miss too much of the expected activity footprint"
    assert 0.55 <= mass_ratio <= 1.8, "Overall activity mass is too far from the expected level"


def test_heatmap_centroid_is_spatially_consistent():
    pred = np.load(OUTPUT_PATH).astype(np.float32)
    ref = load_reference_heatmap()

    pred_cx, pred_cy = weighted_centroid(pred)
    ref_cx, ref_cy = weighted_centroid(ref)
    distance = float(np.hypot(pred_cx - ref_cx, pred_cy - ref_cy))

    assert distance <= 18.0, "Heatmap center of mass drifts too far from the true activity corridor"
