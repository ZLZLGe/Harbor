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

steps = []
cum_l1 = 0.0

for k in range(N):
    u = -K[k] @ dx
    dx = A @ dx + B @ u
    x_abs_next = x_ref + dx
    cum_l1 += float(np.sum(np.abs(u)))
    steps.append(
        {
            'k': k,
            'control': [float(v) for v in u],
            'predicted_temp': [float(v) for v in x_abs_next],
        }
    )

out = {
    'scenario': data['scenario'],
    'horizon': N,
    'initial_temperature': [float(v) for v in data['x0_abs']],
    'steps': steps,
    'cumulative_control_l1': cum_l1,
}

with open('/root/transfer2_hvac_dispatch.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY
