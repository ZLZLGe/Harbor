#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import json


def round6(x: float) -> float:
    return round(float(x), 6)


def pop_std(values):
    m = sum(values) / len(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


with open('/root/training_trace.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

baseline_loss = data['baseline']['val_loss'][-1]
mhc_loss = data['mhc']['val_loss'][-1]
baseline_grad = data['baseline']['grad_norm']
mhc_grad = data['mhc']['grad_norm']

row_err = 0.0
col_err = 0.0
for matrix in data['h_res_matrices']:
    n_rows = len(matrix)
    n_cols = len(matrix[0]) if n_rows else 0
    for row in matrix:
        row_err = max(row_err, abs(sum(row) - 1.0))
    for c in range(n_cols):
        s = 0.0
        for r in range(n_rows):
            s += matrix[r][c]
        col_err = max(col_err, abs(s - 1.0))

out = {
    'scenario': data['scenario'],
    'baseline_final_loss': round6(baseline_loss),
    'mhc_final_loss': round6(mhc_loss),
    'baseline_grad_norm_std': round6(pop_std(baseline_grad)),
    'mhc_grad_norm_std': round6(pop_std(mhc_grad)),
    'baseline_max_grad_norm': round6(max(baseline_grad)),
    'mhc_max_grad_norm': round6(max(mhc_grad)),
    'h_res_max_row_sum_error': round6(row_err),
    'h_res_max_col_sum_error': round6(col_err),
    'preferred_model': 'mhc' if mhc_loss <= baseline_loss else 'baseline',
}

with open('/root/similar_report.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY
