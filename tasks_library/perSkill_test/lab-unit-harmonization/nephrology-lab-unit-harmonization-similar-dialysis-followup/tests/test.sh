#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages pytest pytest-json-ctrf || pip install pytest pytest-json-ctrf

mkdir -p /logs/verifier

cd /root
python3 -m pytest /tests/test_outputs.py -v --tb=short --ctrf /logs/verifier/ctrf.json > /logs/verifier/test_output.log 2>&1

pytest_exit_code=$?
passed=$(grep -oP '\d+(?= passed)' /logs/verifier/test_output.log | tail -1 || echo 0)
failed=$(grep -oP '\d+(?= failed)' /logs/verifier/test_output.log | tail -1 || echo 0)

passed=${passed:-0}
failed=${failed:-0}
total=$((passed + failed))

if [ "$total" -gt 0 ]; then
  python3 - <<PY > /logs/verifier/reward.txt
passed = $passed
total = $total
print(round(passed / total, 3))
PY
else
  if [ "$pytest_exit_code" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
  else
    echo 0 > /logs/verifier/reward.txt
  fi
fi

cat /logs/verifier/test_output.log
exit $pytest_exit_code
