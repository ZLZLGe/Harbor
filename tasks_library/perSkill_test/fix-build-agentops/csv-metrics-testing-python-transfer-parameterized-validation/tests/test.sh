#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

cd /workspace/csv-metrics-lab

set +e
python -m pytest /tests/test_outputs.py -rA -v | tee /logs/verifier/pytest.log
test_status=${PIPESTATUS[0]}
set -e

if [ "$test_status" -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi

exit "$test_status"
