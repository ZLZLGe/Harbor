from pathlib import Path

import numpy as np


def main():
    root = Path("data")
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(17)

    plate = rng.normal(loc=1.5, scale=0.4, size=(9, 6)).astype(np.float32)
    np.save(root / "plate_readings.npy", plate)

    observed = rng.normal(loc=0.0, scale=1.2, size=(5, 3, 4)).astype(np.float32)
    expected = (
        observed * 0.35 + rng.normal(loc=0.0, scale=0.15, size=(5, 3, 4))
    ).astype(np.float32)
    np.savez(root / "residual_bundle.npz", observed=observed, expected=expected)

    x = rng.normal(size=(18, 6)).astype(np.float32)
    true_w = rng.normal(size=(6,)).astype(np.float32)
    margin = x @ true_w + 0.2 * rng.normal(size=(18,)).astype(np.float32)
    y = np.where(margin >= 0, 1.0, -1.0).astype(np.float32)
    w = (true_w * 0.6 + rng.normal(scale=0.1, size=(6,))).astype(np.float32)
    np.savez(root / "binary_panel.npz", x=x, y=y, w=w)

    seq = rng.normal(size=(11, 4)).astype(np.float32)
    Wx = (rng.normal(size=(4, 4)) * 0.18).astype(np.float32)
    Wh = (rng.normal(size=(4, 4)) * 0.12).astype(np.float32)
    b = (rng.normal(size=(4,)) * 0.05).astype(np.float32)
    np.savez(root / "assay_rollout.npz", seq=seq, Wx=Wx, Wh=Wh, b=b)

    X = rng.normal(size=(6, 5)).astype(np.float32)
    W1 = (rng.normal(size=(5, 7)) * 0.22).astype(np.float32)
    b1 = (rng.normal(size=(7,)) * 0.08).astype(np.float32)
    W2 = (rng.normal(size=(7, 3)) * 0.18).astype(np.float32)
    b2 = (rng.normal(size=(3,)) * 0.06).astype(np.float32)
    np.savez(root / "network_stack.npz", X=X, W1=W1, b1=b1, W2=W2, b2=b2)


if __name__ == "__main__":
    main()
