import json
import numpy as np

DATA_PATH = '/root/task_data.json'
OUT_PATH = '/root/transfer3_balance_actions.json'


def test_transfer3_balance_pack_outputs_are_exact():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(OUT_PATH, 'r', encoding='utf-8') as f:
        out = json.load(f)

    A = np.array(data['A'], dtype=float)
    B = np.array(data['B'], dtype=float)
    Q = np.array(data['Q'], dtype=float)
    R = np.array(data['R'], dtype=float)
    x = np.array(data['x0'], dtype=float)
    N = int(data['N'])

    P = [None] * (N + 1)
    K = [None] * N
    P[N] = Q.copy()

    for k in range(N - 1, -1, -1):
        s = R + B.T @ P[k + 1] @ B
        K[k] = np.linalg.solve(s, B.T @ P[k + 1] @ A)
        P[k] = Q + A.T @ P[k + 1] @ (A - B @ K[k])

    controls = []
    score = 0.0
    for k in range(N):
        u = -K[k] @ x
        controls.append(u.copy())
        score += float(x.T @ Q @ x + u.T @ R @ u)
        x = A @ x + B @ u
    score += float(x.T @ Q @ x)

    assert out['scenario'] == data['scenario']
    assert out['horizon'] == N
    assert len(out['first_three_controls']) == 3

    got_controls = np.array(out['first_three_controls'], dtype=float)
    exp_controls = np.array(controls[:3], dtype=float)
    assert np.allclose(got_controls, exp_controls, atol=1e-8)

    assert np.allclose(np.array(out['terminal_state'], dtype=float), x, atol=1e-8)
    assert abs(float(out['quadratic_score']) - score) < 1e-8
