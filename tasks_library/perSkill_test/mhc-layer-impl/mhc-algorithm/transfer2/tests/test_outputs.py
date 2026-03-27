import json
from pathlib import Path

import numpy as np


CASE = Path('/root/transfer2_sensor_case.json')
OUT = Path('/root/transfer2_sensor_fusion_report.json')


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


def softmax(vec):
    v = np.asarray(vec, dtype=float)
    v = v - np.max(v)
    e = np.exp(v)
    return e / np.sum(e)


def test_transfer2_report_matches_reference():
    case = load_json(CASE)
    out = load_json(OUT)

    streams = np.asarray(case['sensor_streams'], dtype=float)
    h_res_logits = np.asarray(case['h_res_logits'], dtype=float)
    h_pre_logits = np.asarray(case['h_pre_logits'][0], dtype=float)
    h_post_logits = np.asarray(case['h_post_logits'][0], dtype=float)
    branch_matrix = np.asarray(case['branch_matrix'], dtype=float)
    reference = np.asarray(case['reference_fused'], dtype=float)

    h_res = sinkhorn_knopp(h_res_logits, int(case['num_iters']), float(case['tau']))
    mixed = np.einsum('st,bnsd->bntd', h_res, streams)

    h_pre = softmax(h_pre_logits)
    branch_input = np.einsum('s,bnsd->bnd', h_pre, streams)
    branch_out = np.einsum('bnd,fd->bnf', branch_input, branch_matrix)

    h_post = softmax(h_post_logits)
    depth_out = np.einsum('bnf,s->bnsf', branch_out, h_post)

    output = mixed + depth_out
    fused_series = np.mean(output, axis=2)[0]

    per_step_std = np.std(output[0], axis=1)
    consistency_curve = np.mean(per_step_std, axis=1)

    row_sums = np.sum(h_res, axis=1)
    col_sums = np.sum(h_res, axis=0)

    assert out['scenario'] == case['scenario']
    assert float(out['tau']) == float(case['tau'])
    assert int(out['num_iters']) == int(case['num_iters'])

    assert np.allclose(np.array(out['fused_series'], dtype=float), fused_series, atol=1e-10)
    assert np.allclose(np.array(out['consistency_curve'], dtype=float), consistency_curve, atol=1e-10)

    sinkhorn = out['sinkhorn']
    assert np.allclose(np.array(sinkhorn['row_sums'], dtype=float), row_sums, atol=1e-10)
    assert np.allclose(np.array(sinkhorn['col_sums'], dtype=float), col_sums, atol=1e-10)
    assert np.isclose(float(sinkhorn['max_row_error']), float(np.max(np.abs(row_sums - 1.0))), atol=1e-12)
    assert np.isclose(float(sinkhorn['max_col_error']), float(np.max(np.abs(col_sums - 1.0))), atol=1e-12)

    metrics = out['metrics']
    mean_consistency = float(np.mean(consistency_curve))
    max_consistency = float(np.max(consistency_curve))
    drift = float(np.linalg.norm(fused_series - reference))
    checksum = float(np.sum(fused_series))

    assert np.isclose(float(metrics['mean_consistency']), mean_consistency, atol=1e-12)
    assert np.isclose(float(metrics['max_consistency']), max_consistency, atol=1e-12)
    assert np.isclose(float(metrics['reference_drift_l2']), drift, atol=1e-12)
    assert np.isclose(float(metrics['output_checksum']), checksum, atol=1e-12)

    # Contract checks.
    assert float(sinkhorn['max_row_error']) < 1e-6
    assert float(sinkhorn['max_col_error']) < 1e-6
    assert drift >= 0.0
