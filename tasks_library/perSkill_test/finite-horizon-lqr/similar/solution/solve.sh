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
state_cost = float(x0.T @ P[0] @ x0)

result = {
    'scenario': data['scenario'],
    'horizon': N,
    'u0': u0.tolist(),
    'predicted_state_after_u0': x1.tolist(),
    'state_cost': state_cost,
}

with open('/root/similar_report.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
PY
