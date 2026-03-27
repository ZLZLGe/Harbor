import json
from pathlib import Path

import numpy as np


CASE = Path('/root/similar_case.json')
OUT = Path('/root/similar_mhc_stability_report.json')


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


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_similar_report_matches_reference():
    case = load_json(CASE)
    out = load_json(OUT)

    residuals = np.asarray(case['residuals'], dtype=float)
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

    assert out['scenario'] == case['scenario']
    assert out['tensor_shape'] == list(output.shape)

    sinkhorn = out['sinkhorn']
    assert np.allclose(np.array(sinkhorn['row_sums'], dtype=float), row_sums, atol=1e-10)
    assert np.allclose(np.array(sinkhorn['col_sums'], dtype=float), col_sums, atol=1e-10)
    assert np.isclose(float(sinkhorn['max_row_error']), float(np.max(np.abs(row_sums - 1.0))), atol=1e-12)
    assert np.isclose(float(sinkhorn['max_col_error']), float(np.max(np.abs(col_sums - 1.0))), atol=1e-12)
    assert np.isclose(float(sinkhorn['min_entry']), float(np.min(h_res)), atol=1e-12)
    assert np.isclose(float(sinkhorn['max_entry']), float(np.max(h_res)), atol=1e-12)

    assert np.allclose(np.array(out['stream_means'], dtype=float), stream_means, atol=1e-10)

    metrics = out['metrics']
    input_energy = float(np.mean(residuals ** 2))
    output_energy = float(np.mean(output ** 2))
    energy_ratio = float(output_energy / input_energy)
    checksum = float(np.sum(output))
    dominant = int(np.argmax(np.abs(stream_means)))

    assert np.isclose(float(metrics['input_energy']), input_energy, atol=1e-12)
    assert np.isclose(float(metrics['output_energy']), output_energy, atol=1e-12)
    assert np.isclose(float(metrics['energy_ratio']), energy_ratio, atol=1e-12)
    assert np.isclose(float(metrics['output_checksum']), checksum, atol=1e-12)
    assert int(metrics['dominant_stream']) == dominant

    # Contract checks: matrix is near doubly stochastic and output is finite.
    assert float(sinkhorn['max_row_error']) < 1e-6
    assert float(sinkhorn['max_col_error']) < 1e-6
    assert np.isfinite(checksum)
