import os

import numpy as np
import pytest


DATA_DIR = "/app/data"
OUTPUT_DIR = "/app"


def output_path(name):
    return os.path.join(OUTPUT_DIR, name)


def logistic_grad(x, y, w):
    margins = y * (x @ w)
    scale = -y / (1.0 + np.exp(margins))
    return np.mean(scale[:, None] * x, axis=0)


def rollout_states(seq, Wx, Wh, b):
    h = np.zeros(Wh.shape[0], dtype=np.float32)
    states = []
    for x_t in seq:
        h = np.tanh(Wx @ x_t + Wh @ h + b).astype(np.float32)
        states.append(h)
    return np.stack(states, axis=0)


def screening_head(X, W1, b1, W2, b2):
    hidden = np.maximum(X @ W1 + b1, 0.0)
    return hidden @ W2 + b2


@pytest.mark.parametrize(
    ("output_name", "expected_fn"),
    [
        (
            "assay_channel_summary.npy",
            lambda: np.load(os.path.join(DATA_DIR, "plate_readings.npy")).mean(axis=0),
        ),
        (
            "residual_energy_map.npy",
            lambda: (
                lambda bundle: np.square(bundle["observed"] - bundle["expected"])
            )(np.load(os.path.join(DATA_DIR, "residual_bundle.npz"))),
        ),
        (
            "binder_loss_grad.npy",
            lambda: (
                lambda panel: logistic_grad(panel["x"], panel["y"], panel["w"])
            )(np.load(os.path.join(DATA_DIR, "binary_panel.npz"))),
        ),
        (
            "assay_state_rollout.npy",
            lambda: (
                lambda rollout: rollout_states(
                    rollout["seq"], rollout["Wx"], rollout["Wh"], rollout["b"]
                )
            )(np.load(os.path.join(DATA_DIR, "assay_rollout.npz"))),
        ),
        (
            "screening_head_logits.npy",
            lambda: (
                lambda network: screening_head(
                    network["X"],
                    network["W1"],
                    network["b1"],
                    network["W2"],
                    network["b2"],
                )
            )(np.load(os.path.join(DATA_DIR, "network_stack.npz"))),
        ),
    ],
)
def test_outputs_match_expected(output_name, expected_fn):
    out = output_path(output_name)
    assert os.path.exists(out), f"Missing output file: {output_name}"
    actual = np.load(out)
    expected = expected_fn()
    assert actual.shape == expected.shape, f"Shape mismatch for {output_name}"
    assert np.all(np.isfinite(actual)), f"Non-finite values found in {output_name}"
    assert np.allclose(actual, expected, rtol=1e-5, atol=1e-6), (
        f"Numerical mismatch for {output_name}"
    )


def test_primary_output_has_full_rollout_length():
    rollout = np.load(os.path.join(DATA_DIR, "assay_rollout.npz"))
    actual = np.load(output_path("assay_state_rollout.npy"))
    assert actual.shape[0] == rollout["seq"].shape[0]
