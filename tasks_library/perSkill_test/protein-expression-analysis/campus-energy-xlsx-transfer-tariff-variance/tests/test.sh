#!/bin/bash
set -uo pipefail

pip3 install --break-system-packages pytest pytest-json-ctrf openpyxl==3.1.5

cd /root
set +e
python3 -m pytest /tests/test_outputs.py -v --tb=short > /logs/verifier/test_output.log 2>&1
PYTEST_EXIT_CODE=$?
set -e

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cat /logs/verifier/test_output.log
exit 0
