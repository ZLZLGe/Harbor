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


def entropy_rows(mat):
    eps = 1e-12
    return -np.sum(mat * np.log(mat + eps), axis=1)


with open('/root/transfer1_router_case.json', 'r', encoding='utf-8') as f:
    case = json.load(f)

window_summaries = []
row_errors = []
col_errors = []
balance_values = []
entropy_values = []

for window in case['windows']:
    logits = np.asarray(window['logits'], dtype=float)
    p = sinkhorn_knopp(logits, int(case['num_iters']), float(case['tau']))

    row_sums = np.sum(p, axis=1)
    col_sums = np.sum(p, axis=0)
    expert_load = col_sums.copy()
    ent = entropy_rows(p)
    entropy_mean = float(np.mean(ent))
    balance_std = float(np.std(expert_load))

    row_errors.append(float(np.max(np.abs(row_sums - 1.0))))
    col_errors.append(float(np.max(np.abs(col_sums - 1.0))))
    balance_values.append(balance_std)
    entropy_values.append(entropy_mean)

    window_summaries.append(
        {
            'window_id': window['window_id'],
            'row_sums': row_sums.tolist(),
            'col_sums': col_sums.tolist(),
            'expert_load': expert_load.tolist(),
            'entropy_mean': entropy_mean,
            'balance_std': balance_std,
        }
    )

best_idx = int(np.argmin(np.asarray(balance_values, dtype=float)))
best_window = case['windows'][best_idx]['window_id']

report = {
    'scenario': case['scenario'],
    'tau': float(case['tau']),
    'num_iters': int(case['num_iters']),
    'window_summaries': window_summaries,
    'global_metrics': {
        'max_row_error': float(np.max(np.asarray(row_errors, dtype=float))),
        'max_col_error': float(np.max(np.asarray(col_errors, dtype=float))),
        'load_std_mean': float(np.mean(np.asarray(balance_values, dtype=float))),
        'mean_entropy': float(np.mean(np.asarray(entropy_values, dtype=float))),
        'best_window_by_balance': best_window,
    },
}

with open('/root/transfer1_router_balance_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
PY
