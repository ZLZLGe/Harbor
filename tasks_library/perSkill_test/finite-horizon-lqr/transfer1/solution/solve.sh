#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import csv
import json
import numpy as np

with open('/root/task_data.json', 'r', encoding='utf-8') as f:
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

with open('/root/transfer1_gimbal_sequence.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['k', 'u_k', 'x1', 'x2', 'x3'])

    for k in range(N):
        u_raw = float((-K[k] @ x.reshape(-1, 1))[0, 0])
        u = float(np.clip(u_raw, u_min, u_max))
        writer.writerow([k, u, float(x[0]), float(x[1]), float(x[2])])
        x = A @ x + (B[:, 0] * u)
PY
