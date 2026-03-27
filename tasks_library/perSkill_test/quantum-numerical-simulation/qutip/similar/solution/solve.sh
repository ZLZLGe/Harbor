#!/bin/bash
set -euo pipefail

python - <<'PY'
from steady_state_lab import build_report, load_problem, save_report

problem = load_problem("/root/steady_state_cases.json")
report = build_report(problem)
save_report(report, "/root/similar_phase_space_report.json")
PY
