#!/bin/bash
set -euo pipefail

cd /root

python3 << 'PY'
import json
import numpy as np


def logsumexp(x, axis, keepdims):
    xmax = np.max(x, axis=axis, keepdims=True)
    stable = x - xmax
    return xmax + np.log(np.sum(np.exp(stable), axis=axis, keepdims=True))


def sinkhorn_knopp(logits, num_iters=20, tau=0.05):
    log_alpha = logits / tau
    for _ in range(num_iters):
        log_alpha = log_alpha - logsumexp(log_alpha, axis=1, keepdims=True)
        log_alpha = log_alpha - logsumexp(log_alpha, axis=0, keepdims=True)
    return np.exp(log_alpha)


with open('/root/transfer3_forecast_case.json', 'r', encoding='utf-8') as f:
    case = json.load(f)

blend_logits = np.asarray(case['blend_logits'], dtype=float)
forecasts = np.asarray(case['forecasts'], dtype=float)  # (horizon, streams)
actuals = np.asarray(case['actuals'], dtype=float)

blend = sinkhorn_knopp(blend_logits, int(case['num_iters']), float(case['tau']))
mixed_streams = forecasts @ blend.T

baseline_ensemble = np.mean(forecasts, axis=1)
mixed_ensemble = np.mean(mixed_streams, axis=1)

baseline_var = float(np.mean(np.var(forecasts, axis=1)))
mixed_var = float(np.mean(np.var(mixed_streams, axis=1)))

baseline_rmse = float(np.sqrt(np.mean((baseline_ensemble - actuals) ** 2)))
mixed_rmse = float(np.sqrt(np.mean((mixed_ensemble - actuals) ** 2)))

row_sums = np.sum(blend, axis=1)
col_sums = np.sum(blend, axis=0)

report = {
    'scenario': case['scenario'],
    'tau': float(case['tau']),
    'num_iters': int(case['num_iters']),
    'baseline_ensemble': baseline_ensemble.tolist(),
    'mixed_ensemble': mixed_ensemble.tolist(),
    'sinkhorn': {
        'row_sums': row_sums.tolist(),
        'col_sums': col_sums.tolist(),
        'max_row_error': float(np.max(np.abs(row_sums - 1.0))),
        'max_col_error': float(np.max(np.abs(col_sums - 1.0))),
    },
    'metrics': {
        'baseline_stream_variance': baseline_var,
        'mixed_stream_variance': mixed_var,
        'variance_reduction': baseline_var - mixed_var,
        'baseline_rmse': baseline_rmse,
        'mixed_rmse': mixed_rmse,
        'rmse_improvement': baseline_rmse - mixed_rmse,
        'mixed_checksum': float(np.sum(mixed_ensemble)),
    },
}

with open('/root/transfer3_forecast_stability_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
PY
