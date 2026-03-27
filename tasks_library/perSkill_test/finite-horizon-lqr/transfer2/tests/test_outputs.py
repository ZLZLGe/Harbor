import json
import numpy as np

DATA_PATH = '/root/task_data.json'
OUT_PATH = '/root/transfer2_hvac_dispatch.json'


def test_transfer2_dispatch_matches_reference_rollout():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(OUT_PATH, 'r', encoding='utf-8') as f:
        out = json.load(f)

    A = np.array(data['A'], dtype=float)
    B = np.array(data['B'], dtype=float)
    Q = np.array(data['Q'], dtype=float)
    R = np.array(data['R'], dtype=float)
    N = int(data['N'])
    x_ref = np.array(data['x_ref'], dtype=float)
    dx = np.array(data['x0_abs'], dtype=float) - x_ref

    P = [None] * (N + 1)
    K = [None] * N
    P[N] = Q.copy()

    for k in range(N - 1, -1, -1):
        s = R + B.T @ P[k + 1] @ B
        K[k] = np.linalg.solve(s, B.T @ P[k + 1] @ A)
        P[k] = Q + A.T @ P[k + 1] @ (A - B @ K[k])

    expected_steps = []
    expected_l1 = 0.0
    for k in range(N):
        u = -K[k] @ dx
        dx = A @ dx + B @ u
        x_abs_next = x_ref + dx
        expected_l1 += float(np.sum(np.abs(u)))
        expected_steps.append((k, u, x_abs_next))

    assert out['scenario'] == data['scenario']
    assert out['horizon'] == N
    assert np.allclose(np.array(out['initial_temperature'], dtype=float), np.array(data['x0_abs'], dtype=float), atol=1e-12)
    assert len(out['steps']) == N

    for got, (k, u, x_next) in zip(out['steps'], expected_steps):
        assert int(got['k']) == k
        assert np.allclose(np.array(got['control'], dtype=float), u, atol=1e-8)
        assert np.allclose(np.array(got['predicted_temp'], dtype=float), x_next, atol=1e-8)

    assert abs(float(out['cumulative_control_l1']) - expected_l1) < 1e-8
