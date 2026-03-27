#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer3_formula_qc_report.md /logs/verifier/ 2>/dev/null || true

exit 0
