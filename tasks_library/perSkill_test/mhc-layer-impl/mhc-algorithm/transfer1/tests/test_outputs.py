import json
from pathlib import Path

import numpy as np


CASE = Path('/root/transfer1_router_case.json')
OUT = Path('/root/transfer1_router_balance_report.json')


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


def entropy_rows(mat):
    eps = 1e-12
    return -np.sum(mat * np.log(mat + eps), axis=1)


def test_transfer1_report_matches_reference():
    case = load_json(CASE)
    out = load_json(OUT)

    assert out['scenario'] == case['scenario']
    assert float(out['tau']) == float(case['tau'])
    assert int(out['num_iters']) == int(case['num_iters'])
    assert len(out['window_summaries']) == len(case['windows'])

    row_errors = []
    col_errors = []
    balance_values = []
    entropy_values = []

    by_id = {item['window_id']: item for item in out['window_summaries']}

    for window in case['windows']:
        wid = window['window_id']
        assert wid in by_id
        got = by_id[wid]

        logits = np.asarray(window['logits'], dtype=float)
        p = sinkhorn_knopp(logits, int(case['num_iters']), float(case['tau']))

        row_sums = np.sum(p, axis=1)
        col_sums = np.sum(p, axis=0)
        expert_load = col_sums.copy()
        entropy_mean = float(np.mean(entropy_rows(p)))
        balance_std = float(np.std(expert_load))

        assert np.allclose(np.array(got['row_sums'], dtype=float), row_sums, atol=1e-10)
        assert np.allclose(np.array(got['col_sums'], dtype=float), col_sums, atol=1e-10)
        assert np.allclose(np.array(got['expert_load'], dtype=float), expert_load, atol=1e-10)
        assert np.isclose(float(got['entropy_mean']), entropy_mean, atol=1e-12)
        assert np.isclose(float(got['balance_std']), balance_std, atol=1e-12)

        row_errors.append(float(np.max(np.abs(row_sums - 1.0))))
        col_errors.append(float(np.max(np.abs(col_sums - 1.0))))
        balance_values.append(balance_std)
        entropy_values.append(entropy_mean)

    gm = out['global_metrics']
    assert np.isclose(float(gm['max_row_error']), float(np.max(np.asarray(row_errors))), atol=1e-12)
    assert np.isclose(float(gm['max_col_error']), float(np.max(np.asarray(col_errors))), atol=1e-12)
    assert np.isclose(float(gm['load_std_mean']), float(np.mean(np.asarray(balance_values))), atol=1e-12)
    assert np.isclose(float(gm['mean_entropy']), float(np.mean(np.asarray(entropy_values))), atol=1e-12)

    best_idx = int(np.argmin(np.asarray(balance_values)))
    expected_best = case['windows'][best_idx]['window_id']
    assert gm['best_window_by_balance'] == expected_best

    # Contract checks.
    assert float(gm['max_row_error']) < 1e-6
    assert float(gm['max_col_error']) < 1e-6
