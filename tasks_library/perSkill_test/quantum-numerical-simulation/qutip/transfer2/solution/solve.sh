#!/bin/bash
set -euo pipefail

python - <<'PY'
from entanglement_lab import build_report, load_problem, save_report

problem = load_problem("/root/entanglement_cases.json")
report = build_report(problem)
save_report(report, "/root/transfer2_entanglement_summary.json")
PY
