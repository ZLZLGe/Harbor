#!/bin/bash
set -euo pipefail

python - <<'PY'
from oscillator_relaxation_lab import build_rows, load_problem, save_rows

problem = load_problem("/root/relaxation_cases.json")
rows = build_rows(problem)
save_rows(rows, "/root/transfer1_relaxation_metrics.csv")
PY
