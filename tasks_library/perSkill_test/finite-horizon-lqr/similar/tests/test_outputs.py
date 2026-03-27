import json
import numpy as np

DATA_PATH = '/root/task_data.json'
OUT_PATH = '/root/similar_report.json'


def test_similar_report_matches_reference_recursion():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(OUT_PATH, 'r', encoding='utf-8') as f:
        out = json.load(f)

    A = np.array(data['A'], dtype=float)
    B = np.array(data['B'], dtype=float)
    Q = np.array(data['Q'], dtype=float)
    R = np.array(data['R'], dtype=float)
    x0 = np.array(data['x0'], dtype=float)
    N = int(data['N'])

    P = [None] * (N + 1)
    K = [None] * N
    P[N] = Q.copy()

    for k in range(N - 1, -1, -1):
        s = R + B.T @ P[k + 1] @ B
        K[k] = np.linalg.solve(s, B.T @ P[k + 1] @ A)
        P[k] = Q + A.T @ P[k + 1] @ (A - B @ K[k])

    u0 = -K[0] @ x0
    x1 = A @ x0 + B @ u0
    cost = float(x0.T @ P[0] @ x0)

    assert out['scenario'] == data['scenario']
    assert out['horizon'] == N
    assert np.allclose(np.array(out['u0'], dtype=float), u0, atol=1e-8)
    assert np.allclose(np.array(out['predicted_state_after_u0'], dtype=float), x1, atol=1e-8)
    assert abs(float(out['state_cost']) - cost) < 1e-8
