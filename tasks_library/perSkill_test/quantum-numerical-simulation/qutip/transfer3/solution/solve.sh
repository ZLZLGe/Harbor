#!/bin/bash
set -euo pipefail

python - <<'PY'
from gate_audit_lab import build_report, load_problem, save_report

problem = load_problem("/root/gate_cases.json")
report = build_report(problem)
save_report(report, "/root/transfer3_gate_audit.json")
PY
