import json
from pathlib import Path

import numpy as np


CASE = Path('/root/transfer3_forecast_case.json')
OUT = Path('/root/transfer3_forecast_stability_report.json')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def test_transfer3_report_matches_reference():
    case = load_json(CASE)
    out = load_json(OUT)

    blend_logits = np.asarray(case['blend_logits'], dtype=float)
    forecasts = np.asarray(case['forecasts'], dtype=float)
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

    assert out['scenario'] == case['scenario']
    assert float(out['tau']) == float(case['tau'])
    assert int(out['num_iters']) == int(case['num_iters'])

    assert np.allclose(np.array(out['baseline_ensemble'], dtype=float), baseline_ensemble, atol=1e-10)
    assert np.allclose(np.array(out['mixed_ensemble'], dtype=float), mixed_ensemble, atol=1e-10)

    sinkhorn = out['sinkhorn']
    assert np.allclose(np.array(sinkhorn['row_sums'], dtype=float), row_sums, atol=1e-10)
    assert np.allclose(np.array(sinkhorn['col_sums'], dtype=float), col_sums, atol=1e-10)
    assert np.isclose(float(sinkhorn['max_row_error']), float(np.max(np.abs(row_sums - 1.0))), atol=1e-12)
    assert np.isclose(float(sinkhorn['max_col_error']), float(np.max(np.abs(col_sums - 1.0))), atol=1e-12)

    metrics = out['metrics']
    assert np.isclose(float(metrics['baseline_stream_variance']), baseline_var, atol=1e-12)
    assert np.isclose(float(metrics['mixed_stream_variance']), mixed_var, atol=1e-12)
    assert np.isclose(float(metrics['variance_reduction']), baseline_var - mixed_var, atol=1e-12)
    assert np.isclose(float(metrics['baseline_rmse']), baseline_rmse, atol=1e-12)
    assert np.isclose(float(metrics['mixed_rmse']), mixed_rmse, atol=1e-12)
    assert np.isclose(float(metrics['rmse_improvement']), baseline_rmse - mixed_rmse, atol=1e-12)
    assert np.isclose(float(metrics['mixed_checksum']), float(np.sum(mixed_ensemble)), atol=1e-12)

    # Contract checks.
    assert float(sinkhorn['max_row_error']) < 1e-6
    assert float(sinkhorn['max_col_error']) < 1e-6
    assert float(metrics['mixed_stream_variance']) <= float(metrics['baseline_stream_variance']) + 1e-12
