import json
import random

import numpy as np
import torch

from data import load_grid_forecast_data
from model import GridForecastConfig, GridLoadTransformer


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def compute_grad_norm(model):
    total = 0.0
    for parameter in model.parameters():
        if parameter.grad is not None:
            total += parameter.grad.detach().norm(2).item() ** 2
    return total ** 0.5


@torch.no_grad()
def evaluate_forecaster(model, dataset, batch_size, device):
    model.eval()
    forecasts = []
    targets = []
    for start in range(0, len(dataset), batch_size):
        end = min(start + batch_size, len(dataset))
        x = dataset.features[start:end].to(device)
        y = dataset.targets[start:end].to(device)
        pred, _ = model(x, y)
        forecasts.append(pred.cpu())
        targets.append(y.cpu())

    forecast = torch.cat(forecasts, dim=0)
    target = torch.cat(targets, dim=0)
    tail_pred = forecast[:, -8:]
    tail_target = target[:, -8:]
    model.train()
    return {
        "mae": float(torch.mean(torch.abs(forecast - target)).item()),
        "rmse": float(torch.sqrt(torch.mean((forecast - target) ** 2)).item()),
        "tail_mae": float(torch.mean(torch.abs(tail_pred - tail_target)).item()),
        "tail_rmse": float(torch.sqrt(torch.mean((tail_pred - tail_target) ** 2)).item()),
    }


def train_variant(model, train_dataset, val_dataset, steps, batch_size, lr, device):
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.02)
    grad_norms = []

    for _ in range(steps):
        x, y = train_dataset.get_batch(batch_size, device)
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        grad_norm = compute_grad_norm(model)
        grad_norms.append(grad_norm)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    report = evaluate_forecaster(model, val_dataset, batch_size=batch_size, device=device)
    grad_mean = float(np.mean(grad_norms))
    grad_std = float(np.std(grad_norms))
    report.update(
        {
            "grad_norm_mean": grad_mean,
            "grad_norm_std": grad_std,
            "grad_norm_cv": float(grad_std / (grad_mean + 1e-8)),
            "max_grad_norm": float(np.max(grad_norms)),
            "steps": steps,
        }
    )
    return report


def build_model(config, variant):
    if variant == "baseline":
        return GridLoadTransformer(config)

    raise NotImplementedError(
        "Implement the constrained multi-stream forecasting variant here and make it expose flow diagnostics."
    )


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    set_seed(2026)
    train_dataset, val_dataset, summary = load_grid_forecast_data()

    config = GridForecastConfig(
        input_dim=summary["num_features"],
        lookback=summary["lookback"],
        horizon=summary["horizon"],
    )

    baseline = build_model(config, "baseline")
    baseline_report = train_variant(
        baseline,
        train_dataset,
        val_dataset,
        steps=160,
        batch_size=32,
        lr=3.5e-3,
        device=device,
    )

    mhc = build_model(config, "mhc")
    mhc_report = train_variant(
        mhc,
        train_dataset,
        val_dataset,
        steps=160,
        batch_size=16,
        lr=2.8e-3,
        device=device,
    )

    payload = {
        "dataset": summary,
        "baseline": baseline_report,
        "mhc": mhc_report,
        "flow_diagnostics": {
            "num_streams": 4,
            "labels": [],
            "h_res_matrices": [],
            "mean_row_abs_error": 0.0,
            "mean_col_abs_error": 0.0,
            "mean_offdiag_share": 0.0,
        },
    }

    with open("/root/grid_forecast_summary.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
