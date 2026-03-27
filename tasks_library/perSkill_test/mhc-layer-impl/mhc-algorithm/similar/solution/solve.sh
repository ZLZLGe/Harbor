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


with open('/root/similar_case.json', 'r', encoding='utf-8') as f:
    case = json.load(f)

residuals = np.asarray(case['residuals'], dtype=float)  # (b, n, s, d)
h_res_logits = np.asarray(case['h_res_logits'], dtype=float)
h_pre_logits = np.asarray(case['h_pre_logits'][0], dtype=float)
h_post_logits = np.asarray(case['h_post_logits'][0], dtype=float)
branch_matrix = np.asarray(case['branch_matrix'], dtype=float)

h_res = sinkhorn_knopp(h_res_logits, int(case['num_iters']), float(case['tau']))
residuals_mixed = np.einsum('st,bnsd->bntd', h_res, residuals)

h_pre = softmax(h_pre_logits)
branch_input = np.einsum('s,bnsd->bnd', h_pre, residuals)
branch_out = np.einsum('bnd,fd->bnf', branch_input, branch_matrix)

h_post = softmax(h_post_logits)
depth_out = np.einsum('bnf,s->bnsf', branch_out, h_post)

output = residuals_mixed + depth_out

row_sums = np.sum(h_res, axis=1)
col_sums = np.sum(h_res, axis=0)
stream_means = np.mean(output, axis=(0, 1, 3))

input_energy = float(np.mean(residuals ** 2))
output_energy = float(np.mean(output ** 2))
energy_ratio = float(output_energy / input_energy)
output_checksum = float(np.sum(output))
dominant_stream = int(np.argmax(np.abs(stream_means)))

report = {
    'scenario': case['scenario'],
    'sinkhorn': {
        'row_sums': row_sums.tolist(),
        'col_sums': col_sums.tolist(),
        'max_row_error': float(np.max(np.abs(row_sums - 1.0))),
        'max_col_error': float(np.max(np.abs(col_sums - 1.0))),
        'min_entry': float(np.min(h_res)),
        'max_entry': float(np.max(h_res)),
    },
    'stream_means': stream_means.tolist(),
    'metrics': {
        'input_energy': input_energy,
        'output_energy': output_energy,
        'energy_ratio': energy_ratio,
        'output_checksum': output_checksum,
        'dominant_stream': dominant_stream,
    },
    'tensor_shape': list(output.shape),
}

with open('/root/similar_mhc_stability_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
PY
