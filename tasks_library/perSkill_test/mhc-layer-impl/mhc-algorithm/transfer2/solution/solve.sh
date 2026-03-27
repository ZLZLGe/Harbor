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


def softmax(vec):
    v = np.asarray(vec, dtype=float)
    v = v - np.max(v)
    e = np.exp(v)
    return e / np.sum(e)


with open('/root/transfer2_sensor_case.json', 'r', encoding='utf-8') as f:
    case = json.load(f)

sensor_streams = np.asarray(case['sensor_streams'], dtype=float)  # (b, n, s, d)
h_res_logits = np.asarray(case['h_res_logits'], dtype=float)
h_pre_logits = np.asarray(case['h_pre_logits'][0], dtype=float)
h_post_logits = np.asarray(case['h_post_logits'][0], dtype=float)
branch_matrix = np.asarray(case['branch_matrix'], dtype=float)
reference = np.asarray(case['reference_fused'], dtype=float)

h_res = sinkhorn_knopp(h_res_logits, int(case['num_iters']), float(case['tau']))
mixed = np.einsum('st,bnsd->bntd', h_res, sensor_streams)

h_pre = softmax(h_pre_logits)
branch_input = np.einsum('s,bnsd->bnd', h_pre, sensor_streams)
branch_out = np.einsum('bnd,fd->bnf', branch_input, branch_matrix)

h_post = softmax(h_post_logits)
depth_out = np.einsum('bnf,s->bnsf', branch_out, h_post)

output = mixed + depth_out
fused = np.mean(output, axis=2)  # (b, n, d)
fused_series = fused[0]

per_step_std = np.std(output[0], axis=1)  # (n, d)
consistency_curve = np.mean(per_step_std, axis=1)  # (n,)

row_sums = np.sum(h_res, axis=1)
col_sums = np.sum(h_res, axis=0)

report = {
    'scenario': case['scenario'],
    'tau': float(case['tau']),
    'num_iters': int(case['num_iters']),
    'fused_series': fused_series.tolist(),
    'consistency_curve': consistency_curve.tolist(),
    'sinkhorn': {
        'row_sums': row_sums.tolist(),
        'col_sums': col_sums.tolist(),
        'max_row_error': float(np.max(np.abs(row_sums - 1.0))),
        'max_col_error': float(np.max(np.abs(col_sums - 1.0))),
    },
    'metrics': {
        'mean_consistency': float(np.mean(consistency_curve)),
        'max_consistency': float(np.max(consistency_curve)),
        'reference_drift_l2': float(np.linalg.norm(fused_series - reference)),
        'output_checksum': float(np.sum(fused_series)),
    },
}

with open('/root/transfer2_sensor_fusion_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
PY
