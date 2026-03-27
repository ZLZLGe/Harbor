import csv
import json
import numpy as np

DATA_PATH = '/root/task_data.json'
OUT_PATH = '/root/transfer1_gimbal_sequence.csv'


def test_transfer1_sequence_is_correct_and_clipped():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    A = np.array(data['A'], dtype=float)
    B = np.array(data['B'], dtype=float)
    Q = np.array(data['Q'], dtype=float)
    R = np.array(data['R'], dtype=float)
    x = np.array(data['x0'], dtype=float)
    N = int(data['N'])
    u_min = float(data['u_min'])
    u_max = float(data['u_max'])

    P = [None] * (N + 1)
    K = [None] * N
    P[N] = Q.copy()

    for k in range(N - 1, -1, -1):
        s = R + B.T @ P[k + 1] @ B
        K[k] = np.linalg.solve(s, B.T @ P[k + 1] @ A)
        P[k] = Q + A.T @ P[k + 1] @ (A - B @ K[k])

    expected_rows = []
    for k in range(N):
        u_raw = float((-K[k] @ x.reshape(-1, 1))[0, 0])
        u = float(np.clip(u_raw, u_min, u_max))
        expected_rows.append((k, u, float(x[0]), float(x[1]), float(x[2])))
        x = A @ x + (B[:, 0] * u)

    with open(OUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == ['k', 'u_k', 'x1', 'x2', 'x3']
    assert len(rows) == N

    for got, exp in zip(rows, expected_rows):
        assert int(got['k']) == exp[0]
        assert abs(float(got['u_k']) - exp[1]) < 1e-8
        assert abs(float(got['x1']) - exp[2]) < 1e-8
        assert abs(float(got['x2']) - exp[3]) < 1e-8
        assert abs(float(got['x3']) - exp[4]) < 1e-8
        assert u_min - 1e-12 <= float(got['u_k']) <= u_max + 1e-12
