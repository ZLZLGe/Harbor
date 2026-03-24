from pathlib import Path

import numpy as np
import torch


FEATURE_NAMES = [
    "load_mw",
    "temp_c",
    "humidity_pct",
    "wind_mps",
    "solar_index",
    "industrial_index",
    "congestion_index",
    "hour_sin",
    "hour_cos",
    "week_sin",
    "week_cos",
]


class WindowDataset:
    def __init__(self, features, targets):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32)

    def get_batch(self, batch_size, device="cpu"):
        indices = torch.randint(0, self.targets.shape[0], (batch_size,))
        x = self.features[indices].to(device)
        y = self.targets[indices].to(device)
        return x, y

    def __len__(self):
        return int(self.targets.shape[0])


def _build_windows(features, target, lookback, horizon):
    windows = []
    labels = []
    total = target.shape[0] - lookback - horizon + 1
    for start in range(total):
        end = start + lookback
        windows.append(features[start:end])
        labels.append(target[end : end + horizon])
    return np.stack(windows).astype(np.float32), np.stack(labels).astype(np.float32)


def load_grid_forecast_data(
    path="/root/data/grid_dispatch_panel.csv",
    lookback=72,
    horizon=24,
    train_ratio=0.78,
):
    table = np.genfromtxt(path, delimiter=",", names=True, encoding="utf-8")
    raw_features = np.stack([table[name].astype(np.float32) for name in FEATURE_NAMES], axis=1)
    target = table["load_mw"].astype(np.float32)

    split_index = int(raw_features.shape[0] * train_ratio)
    mean = raw_features[:split_index].mean(axis=0, keepdims=True)
    std = raw_features[:split_index].std(axis=0, keepdims=True) + 1e-6
    normalized = (raw_features - mean) / std

    windows, labels = _build_windows(normalized, target, lookback=lookback, horizon=horizon)
    window_split = int(windows.shape[0] * train_ratio)

    train_dataset = WindowDataset(windows[:window_split], labels[:window_split])
    val_dataset = WindowDataset(windows[window_split:], labels[window_split:])
    summary = {
        "train_windows": len(train_dataset),
        "val_windows": len(val_dataset),
        "lookback": lookback,
        "horizon": horizon,
        "num_features": len(FEATURE_NAMES),
        "target": "load_mw",
        "feature_names": FEATURE_NAMES,
    }
    return train_dataset, val_dataset, summary


if __name__ == "__main__":
    train_dataset, val_dataset, summary = load_grid_forecast_data(
        Path(__file__).resolve().parent.parent / "data" / "grid_dispatch_panel.csv"
    )
    print(summary)
    print("train windows:", len(train_dataset))
    print("val windows:", len(val_dataset))
