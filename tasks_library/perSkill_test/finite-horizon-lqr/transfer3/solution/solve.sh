#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
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
    score += float(x.T @ Q @ x + u.T @ R @ u)
    controls.append([float(v) for v in u])
    x = A @ x + B @ u

score += float(x.T @ Q @ x)

out = {
    'scenario': data['scenario'],
    'horizon': N,
    'first_three_controls': controls[:3],
    'terminal_state': [float(v) for v in x],
    'quadratic_score': score,
}

with open('/root/transfer3_balance_actions.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY
